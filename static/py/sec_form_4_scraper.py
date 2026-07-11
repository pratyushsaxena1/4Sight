import requests
from bs4 import BeautifulSoup
import pandas as pd
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

# SEC's fair-access policy returns 403 ("Undeclared Automated Tool") for
# browser-spoofed User-Agents. It requires a declared User-Agent that names the
# app and a contact email. See https://www.sec.gov/os/webmaster-faq#developers
SEC_USER_AGENT = "4Sight Form4 Viewer admin@4sight.app"


def get_form_4_filings(cik):
    """Return a DataFrame of a company's recent Form 4 filings (most recent first),
    each with a link to the filing's index page."""
    base_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&count=100&output=atom"
    headers = {"User-Agent": SEC_USER_AGENT}
    try:
        response = requests.get(base_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            entries = soup.find_all('entry')
            if not entries:
                return None
            form_4_data = []
            for entry in entries:
                title = entry.find('title').text
                updated = entry.find('updated').text
                link = entry.find('link')['href']
                form_4_data.append({'Title': title, 'Date': updated, 'Link': link})
            return pd.DataFrame(form_4_data)
        else:
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def find_form4_xml(index_url):
    """Return the URL of a filing's primary Form 4 XML (the machine-readable
    `ownershipDocument`), or None.

    Every Form 4 has one, regardless of which vendor filed it. On the index page
    the bare `*.xml` link is the data document; the `xslF345X0*/...` link is only
    its human-readable HTML rendering, so we skip that one.
    """
    headers = {"User-Agent": SEC_USER_AGENT}
    try:
        response = requests.get(index_url, headers=headers)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.content, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.lower().endswith('.xml') and 'xslf345' not in href.lower():
                return "https://www.sec.gov" + href
    except Exception as e:
        print(f"Error fetching index {index_url}: {e}")
    return None


def parse_form4_xml(url):
    """Parse a Form 4 ownership XML into non-derivative transaction rows.

    The `ownershipDocument` schema is standardized by the SEC, so this works for
    any company. Rows are formatted to match the app's expected CSV columns.
    """
    headers = {"User-Agent": SEC_USER_AGENT}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return pd.DataFrame()
        root = ET.fromstring(response.content)
        issuer = (root.findtext('.//issuer/issuerName') or '').strip() or 'Unknown'

        rows = []
        for txn in root.findall('.//nonDerivativeTransaction'):
            date = txn.findtext('.//transactionDate/value')
            shares = txn.findtext('.//transactionShares/value')
            acquired_disposed = txn.findtext('.//transactionAcquiredDisposedCode/value')
            price = txn.findtext('.//transactionPricePerShare/value')

            # A Form 4 may also hold derivative-only or holding-only rows; skip
            # anything missing the fields the app needs.
            if not (date and shares and acquired_disposed):
                continue

            try:
                date = datetime.strptime(date[:10], '%Y-%m-%d').strftime('%m/%d/%Y')
            except (ValueError, TypeError):
                pass
            try:
                shares = '{:,}'.format(int(float(shares)))
            except (ValueError, TypeError):
                pass
            try:
                price = f'${float(price):,.2f}' if price and float(price) != 0 else 'N/A'
            except (ValueError, TypeError):
                price = 'N/A'

            rows.append({
                'Title': issuer,
                'Transaction Date': date,
                'Acquired_Disposed': acquired_disposed,
                'Amount': shares,
                'Price': price,
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return pd.DataFrame()


def scrape_form_4(cik, max_filings=25):
    """Scrape Form 4 filings for a CIK and return a DataFrame (empty if none found).

    Runs entirely in-process so it works on serverless platforms where spawning
    a `python3` subprocess and writing to the project directory are not possible.
    Only the most recent `max_filings` filings are processed so a live scrape
    fits inside a serverless function's time limit (each filing costs two
    sequential SEC requests: the index page and the XML document).
    """
    df = get_form_4_filings(cik)
    if df is None:
        return pd.DataFrame()

    # The atom feed returns filings most-recent-first; cap how many we fetch.
    links = list(df['Link'])[:max_filings]

    frames = []
    for link in links:
        xml_url = find_form4_xml(link)
        if not xml_url:
            continue
        frame = parse_form4_xml(xml_url)
        if not frame.empty:
            frames.append(frame)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Format to run program: python sec_form_4_scraper.py <CIK>")
        sys.exit(1)
    cik = sys.argv[1]
    final_df = scrape_form_4(cik)
    if not final_df.empty:
        final_df.to_csv('form_4_filings.csv', index=False)
        print("Data has been saved to form_4_filings.csv")
    else:
        print("No data retrieved")
