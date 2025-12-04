import requests
from bs4 import BeautifulSoup
import pandas as pd
import xml.etree.ElementTree as ET
import sys
import yfinance as yf
import pandas as pd
from googletrans import Translator
from datetime import datetime, timedelta
from textblob import TextBlob
import csv
import nltk 
from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize, sent_tokenize 
nltk.download('punkt_tab', force=True)

# Get news article titles and descriptions and translate to English if it's in a different language. Returns all the article titles and descriptions in an array of tuples.
def get_news(company, amount, price, a_or_d, date):
    all_news = []
    today = datetime.today()
    one_month_ago = today - timedelta(days=30)
    from_date = one_month_ago.strftime('%Y-%m-%d')
    api_key = 'd508bd3e229f42318109096b7e028760'
    url = f"https://newsapi.org/v2/everything?q={company}&from={from_date}&sortBy=publishedAt&apiKey={api_key}"
    response = requests.get(url)
    data = response.json()
    translator = Translator()
    for article in data["articles"]:
        try:
            title_translation = translator.translate(str(article["title"]), dest='en')
            description_translation = translator.translate(str(article["description"]), dest='en')
            title = title_translation.text
            description = description_translation.text
            if (company.lower() in title.lower() or company.lower() in description.lower()):
                all_news.append((title, description))
        except:
            continue
    return all_news

# Use this to get the closing price to get the actual trade value on normal market
def get_stock_data(stock_symbol):
    stock_data = yf.download(stock_symbol, '2020-01-01', None)
    stock_data.reset_index(inplace=True)
    stock_data['Date'] = stock_data['Date'].dt.strftime('%Y-%m-%d')
    stock_data.sort_values(by='Date', ascending=False, inplace=True)
    return stock_data.to_dict('records')

# Convert the company name into a ticker symbol
def get_ticker(company_name):
    yfinance = "https://query2.finance.yahoo.com/v1/finance/search"
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    params = {"q": company_name, "quotes_count": 1, "country": "United States"}
    res = requests.get(url=yfinance, params=params, headers={'User-Agent': user_agent})
    data = res.json()
    company_code = data['quotes'][0]['symbol']
    return company_code

# Get the significance of the trade and quantify it
def quantify_information(company, amount, price, a_or_d, date):
    stock_symbol = get_ticker(company)
    closing_price = get_stock_data(stock_symbol)[0][('Close', str(stock_symbol))]
    actual_value = 1 / closing_price
    trade_value = amount / price
    trade_quantifier = trade_value / actual_value
    if a_or_d == "D":
        trade_quantifier *= -1
    low_threshold = 0.8
    high_threshold = 1.2
    trade_significance = 0
    if trade_quantifier < low_threshold:  # Below market value
        if trade_quantifier < 0:  # Selling at a low price
            trade_significance = 1  # Likely dumping stock
        else:  # Buying at a low price
            trade_significance = 3  # Insider sees undervaluation
    elif trade_quantifier > high_threshold:  # Above market value
        if trade_quantifier > 0:  # Buying at a high price
            trade_significance = 4  # Speculative risk or insider overconfidence
        else:  # Selling at a high price
            trade_significance = 2  # Cashing in on hype/insider confidence
    return trade_significance

# Based on the trade significance and the current news, find a pattern and generate an explanation as to why this trade was made
def generate_explanation(company, amount, price, a_or_d, date, current_news):
    trade_signifiance = quantify_information(company, amount, price, a_or_d, date)
    explanations = {
        0: "The trade was made at a relatively neutral price. This doesn't seem to indicate any major insider knowledge or expected changes in the stock price.",
        1: "Insiders are selling at a significantly low price. This could suggest they are trying to offload shares quickly, possibly anticipating bad news or a decline in the company's stock value.",
        2: "Insiders are selling at a significantly high price. This might indicate strong insider confidence in the company's performance or an attempt to capitalize on current hype or positive trends.",
        3: "Insiders are buying at a significantly low price. This suggests they believe the stock is undervalued and expect future growth or recovery.",
        4: "Insiders are buying at a significantly high price. This could indicate strong confidence in the company despite a high valuation, potentially due to inside knowledge of upcoming success."
    }
    summary = analyze_news(current_news, trade_signifiance)
    explanation = explanations.get(trade_signifiance) + " Current events that may have caused the insider to make this trade include: " + summary + "."
    return explanation

# Determine the sentiment of the news to see how it may impact the stock of the company
def analyze_news(current_news, trade_significance):
    # Add things that are good/bad, then based on the net company success, return a summary of the good/bad news as a potential explanantion as to why a trade was made
    good_news = []
    bad_news = []
    summary = ""
    for news in current_news:
        sentiment = get_sentiment(str(news))
        if sentiment == 1:
            good_news.append(str(news))
        elif sentiment == -1:
            bad_news.append(str(news))
    if trade_significance == 1:
        for t in bad_news:
            summary += str(t)
    elif trade_significance == 2 or trade_significance == 3 or trade_significance == 4:
        for t in good_news:
            summary += str(t)
    else:
        summary = "There don't seem to be any current events or news that may point to a positive or negative impact on the stock of the company."
    return summary

# Summarize the text
def summarize(text):
    stopWords = set(stopwords.words("english")) 
    words = word_tokenize(text, language="english")
    freqTable = dict() 
    for word in words: 
        word = word.lower() 
        if word in stopWords: 
            continue
        if word in freqTable: 
            freqTable[word] += 1
        else: 
            freqTable[word] = 1
    sentences = sent_tokenize(text) 
    sentenceValue = dict() 
    for sentence in sentences: 
        for word, freq in freqTable.items(): 
            if word in sentence.lower(): 
                if sentence in sentenceValue: 
                    sentenceValue[sentence] += freq 
                else: 
                    sentenceValue[sentence] = freq 
    sumValues = 0
    for sentence in sentenceValue: 
        sumValues += sentenceValue[sentence]
    average = int(sumValues / len(sentenceValue))
    summary = '' 
    for sentence in sentences: 
        if (sentence in sentenceValue) and (sentenceValue[sentence] > (1.2 * average)): 
            summary += " " + sentence
    return summary

# Find sentiment of news
def get_sentiment(news):
    sentiment = 0
    blob = TextBlob(news)
    polarity = blob.sentiment.polarity
    if polarity > 0.2:
        sentiment = 1
    elif polarity < -0.2:
        sentiment = -1
    return sentiment

def main():
    with open('../../form_4_filings.csv', 'r') as file:
        csv_reader = csv.reader(file)
        _ = next(csv_reader)
        for row in csv_reader:
            file.seek(0)
            next(csv_reader)
            data = list(csv_reader)
    company = data[1][0]
    amount = data[1][3]
    price = data[1][4]
    a_or_d = data[1][2]
    date = data[1][1]
    result = generate_explanation(company, amount, price, a_or_d, date, get_news(company, amount, price, a_or_d, date))
    print(result)
    return result

main()