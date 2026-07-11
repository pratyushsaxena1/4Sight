from flask import Flask, render_template, request
import csv
import requests
import json
import os
from anthropic import Anthropic
from static.py.graphs import preprocess_form_4_data, generate_stock_plot, generate_stock_analysis
from static.py.sec_form_4_scraper import scrape_form_4

app = Flask(__name__)

# Absolute paths so file access works regardless of the serverless working directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLED_CSV = os.path.join(BASE_DIR, 'form_4_filings.csv')
# Serverless filesystems are read-only except for /tmp, so live scrapes are written there.
WRITABLE_CSV = '/tmp/form_4_filings.csv'


def get_ticker(company_name):
    yfinance = "https://query2.finance.yahoo.com/v1/finance/search"
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    params = {"q": company_name, "quotes_count": 1, "country": "United States"}
    res = requests.get(url=yfinance, params=params, headers={'User-Agent': user_agent})
    data = res.json()
    company_code = data['quotes'][0]['symbol']
    return company_code

def get_cik_from_ticker(ticker):
    json_file_path = os.path.join(BASE_DIR, 'static', 'py', 'tickertocik.json')
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        for value in data.values():
            if value['ticker'].lower() == ticker.lower():
                return value['cik_str']
        return f"No CIK found for ticker: {ticker}"
    except FileNotFoundError:
        return "Error: JSON file not found. Check the file path."
    except json.JSONDecodeError:
        return "Error: Failed to parse the JSON file. Ensure it is a valid JSON format."
    except Exception as e:
        return f"Error fetching CIK: {str(e)}"

def preprocess_data(data):
    processed_data = []
    for row in data:
        if row[0] and row[1] and row[2] and row[3] and row[4]:
            row[4] = row[4].split('(')[0].strip()
            processed_data.append(row)
    return processed_data

@app.route('/', methods=['GET', 'POST'])
def index():
    data = []
    search_query = ""
    csv_path = None

    if request.method == 'POST':
        search_query = request.form.get('companySearchText', '').lower()
        try:
            cik = get_cik_from_ticker(get_ticker(search_query))
            df = scrape_form_4(cik)
            if df is not None and not df.empty:
                df.to_csv(WRITABLE_CSV, index=False)
                # A search scrapes exactly one company, so show every row it
                # returned. (Don't re-filter by company name — SEC labels some
                # filings' title as "Common Stock", which would drop them.)
                csv_path = WRITABLE_CSV
        except Exception as e:
            print(f"Search/scrape failed: {e}")
    else:
        # No search: show the bundled snapshot.
        csv_path = BUNDLED_CSV

    if csv_path:
        with open(csv_path, 'r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # skip header
            data = [row for row in csv_reader if row]

    data = preprocess_data(data)
    return render_template('index.html', data=data, search_query=search_query)

@app.route('/visualization', methods=['GET', 'POST'])
def visualization():
    # The company to visualize comes from the home-page search (passed through as
    # ?company=...) or the search box on this page. Without it, fall back to the
    # bundled snapshot.
    company = request.values.get('company', '').strip()
    selected_company = None
    plot_img = None
    error = None
    df = None

    try:
        if company:
            # Scrape the requested company live, exactly like the home search.
            cik = get_cik_from_ticker(get_ticker(company))
            scraped = scrape_form_4(cik)
            if scraped.empty:
                error = f"No Form 4 data found for '{company}'."
            else:
                scraped.to_csv(WRITABLE_CSV, index=False)
                df = preprocess_form_4_data(WRITABLE_CSV)
                selected_company = company.title()
        else:
            df = preprocess_form_4_data(BUNDLED_CSV)
            selected_company = df['Title'].mode()[0] if not df.empty else None

        if error is None and df is not None and not df.empty:
            # Plot all of the company's filings (one company per page).
            plot_img = generate_stock_plot(df)
        elif error is None:
            error = "No data available to visualize."
    except Exception as e:
        error = f"Could not build visualization for '{company}': {e}"
        print(f"Visualization error: {e}")

    return render_template('visualization.html',
                           selected_company=selected_company,
                           plot_img=plot_img,
                           error=error)

@app.route('/analysis', methods=['GET', 'POST'])
def analysis():
    # Analyze the company passed from the home page (?company=...) or the search
    # box on this page. Without one, fall back to the bundled snapshot.
    company = request.values.get('company', '').strip()
    selected_company = None
    company_data = []

    try:
        if company:
            cik = get_cik_from_ticker(get_ticker(company))
            scraped = scrape_form_4(cik)
            if not scraped.empty:
                company_data = scraped.values.tolist()
                selected_company = company.title()
        else:
            with open(BUNDLED_CSV, 'r') as file:
                csv_reader = csv.reader(file)
                next(csv_reader)
                company_data = [row for row in csv_reader if row]
                selected_company = "Amazon (sample data)"
    except Exception as e:
        print(f"Analysis data error: {e}")

    # Gather data before spending anything on the model: bail out (no API call)
    # if there's nothing to analyze or no key configured.
    if not company_data:
        msg = (f"No Form 4 data found for '{company}'." if company
               else "No data available to analyze.")
        return render_template('analysis.html', output=msg, selected_company=selected_company)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return render_template('analysis.html',
                               output="AI analysis is unavailable: the ANTHROPIC_API_KEY environment variable is not set.",
                               selected_company=selected_company)

    label = selected_company or "this company"
    prompt = (f"The following data is from {label}'s SEC Form 4 filings. Don't italicize or bold any text. "
              "Don't give any background on Form 4 Filings or confirm you understood the prompt "
              "or have any headers or anything like that. All i want you to do is to explain "
              "possible reasons for the trends in this data, especially based on current news "
              "regarding the company, in a numbered list format:" + str(company_data))

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )
        output = "".join(block.text for block in response.content if block.type == "text")
    except Exception as e:
        output = f"AI analysis failed: {e}"

    return render_template('analysis.html', output=output, selected_company=selected_company)

if __name__ == '__main__':
    app.run(debug=True)
