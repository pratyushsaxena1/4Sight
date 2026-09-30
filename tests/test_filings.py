import base64
from io import StringIO
from types import SimpleNamespace

import pytest

from static.py import sec_form_4_scraper as scraper
from static.py.graphs import preprocess_form_4_data, generate_stock_plot


def test_ownership_xml_extracts_only_complete_transactions(monkeypatch):
    xml = b"""<ownershipDocument>
      <issuer><issuerName>Example Corp</issuerName></issuer>
      <nonDerivativeTable>
        <nonDerivativeTransaction>
          <transactionDate><value>2026-09-01</value></transactionDate>
          <transactionAmounts>
            <transactionShares><value>1500</value></transactionShares>
            <transactionPricePerShare><value>12.5</value></transactionPricePerShare>
            <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
          </transactionAmounts>
        </nonDerivativeTransaction>
        <nonDerivativeTransaction><transactionDate><value>2026-09-01</value></transactionDate></nonDerivativeTransaction>
      </nonDerivativeTable>
    </ownershipDocument>"""
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: SimpleNamespace(status_code=200, content=xml))
    assert scraper.parse_form4_xml("https://example.com/filing.xml").to_dict("records") == [{
        "Title": "Example Corp", "Transaction Date": "09/01/2026",
        "Acquired_Disposed": "A", "Amount": "1,500", "Price": "$12.50",
    }]


def test_xml_lookup_skips_html_rendering(monkeypatch):
    html = b'<a href="/Archives/xslF345X05/filing.xml">HTML</a><a href="/Archives/filing.xml">XML</a>'
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: SimpleNamespace(status_code=200, content=html))
    assert scraper.find_form4_xml("https://example.com/index") == "https://www.sec.gov/Archives/filing.xml"


@pytest.mark.parametrize("status,content", [(403, b"Forbidden"), (200, b"not XML")])
def test_failed_xml_fetch_returns_empty(monkeypatch, status, content):
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: SimpleNamespace(status_code=status, content=content))
    assert scraper.parse_form4_xml("https://example.com/filing.xml").empty


def test_cleanup_and_chart():
    data = StringIO('Title,Transaction Date,Acquired_Disposed,Amount,Price\nExample,09/01/2026,A,"1,500","$1,234.50"\nExample,09/02/2026,D,300,$25.00\nExample,09/03/2026,A,10,N/A\n')
    frame = preprocess_form_4_data(data)
    assert frame["Amount"].tolist() == [1500, 300]
    assert frame["Price"].tolist() == [1234.5, 25.0]
    assert frame["Acquired_Disposed"].tolist() == ["Acquired", "Disposed"]
    assert base64.b64decode(generate_stock_plot(frame)).startswith(b"\x89PNG\r\n\x1a\n")


def test_bundled_routes_work_without_network(monkeypatch):
    import app

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    def no_network(*args, **kwargs):
        raise AssertionError("Bundled demo must not call external services")
    monkeypatch.setattr(app.requests, "get", no_network)
    client = app.app.test_client()
    for route in ["/", "/visualization", "/analysis"]:
        response = client.get(route)
        assert response.status_code == 200
    assert b"AMAZON" in client.get("/").data
    assert b"base64," in client.get("/visualization").data
    assert b"ANTHROPIC_API_KEY" in client.get("/analysis").data
