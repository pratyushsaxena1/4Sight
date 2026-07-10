from flask import Flask, render_template, request
import csv
import requests
import json
import os
from google import genai
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
    csv_path = BUNDLED_CSV
    if request.method == 'POST':
        search_query = request.form.get('companySearchText', '').lower()
        try:
            cik = get_cik_from_ticker(get_ticker(search_query))
            df = scrape_form_4(cik)
            if df is not None and not df.empty:
                df.to_csv(WRITABLE_CSV, index=False)
                csv_path = WRITABLE_CSV
        except Exception as e:
            print(f"Search/scrape failed: {e}")

    with open(csv_path, 'r') as file:
        csv_reader = csv.reader(file)
        _ = next(csv_reader)
        for row in csv_reader:
            if search_query in row[0].lower():
                data.append(row)
        if not search_query:
            file.seek(0)
            next(csv_reader)
            data = list(csv_reader)
    data = preprocess_data(data)
    return render_template('index.html', data=data)

@app.route('/visualization', methods=['GET', 'POST'])
def visualization():
    companies = []
    selected_company = None
    plot_img = None
    stock_analysis = None

    try:
        df = preprocess_form_4_data(BUNDLED_CSV)
        companies = list(set(df['Title']))
        if companies:
            selected_company = companies[0]
            # Filter data for the selected company
            company_data = df[df['Title'] == selected_company]

            # Generate plot (returned as a base64 PNG) and analysis
            plot_img = generate_stock_plot(company_data)
            stock_analysis = generate_stock_analysis(company_data)
    except Exception as e:
        companies = ["No companies found"]
        print(f"Error reading companies: {e}")

    return render_template('visualization.html',
                           companies=companies,
                           selected_company=selected_company,
                           plot_img=plot_img,
                           stock_analysis=stock_analysis)

@app.route('/analysis')
def analysis():
    try:
        with open(BUNDLED_CSV, 'r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)
            company_data = [row for row in csv_reader if row]
    except Exception as e:
        company_data = ["No companies found"]
        print(f"Error reading companies: {e}")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return render_template('analysis.html',
                               output="AI analysis is unavailable: the GEMINI_API_KEY environment variable is not set.")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="The following data is from Form 4 Filings. Don't italicize or bold any text. Don't give any background on Form 4 Filings or confirm you understood the prompt or have any headers or anything like that. All i want you to do is to explain possible reasons for the trends in this data, especially based on current news regarding the company, in a numbered list format:" + str(company_data)
        )
        output = response.text
    except Exception as e:
        output = f"AI analysis failed: {e}"

    return render_template('analysis.html', output=output)

if __name__ == '__main__':
    app.run(debug=True)
