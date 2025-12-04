import requests
from bs4 import BeautifulSoup
import pandas as pd
import sys
import re
import xml.etree.ElementTree as ET

def get_form_4_filings(cik):
    base_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&count=100&output=atom"
    headers = {"User-Agent": 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'}
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

def find_wk_form4_links(page_url, cik):
    headers = {"User-Agent": 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'}
    try:
        response = requests.get(page_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            pattern1 = re.compile(r'wk-form4_.*\.xml', re.IGNORECASE)
            pattern2 = re.compile(r'edgardoc', re.IGNORECASE)
            matched_links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if pattern1.search(href):
                    matched_links.append("https://sec.gov" + href)
                if pattern2.search(href):
                    matched_links.append("https://sec.gov" + href)
            return matched_links
        else:
            return []
    except Exception as e:
        print(f"Error fetching page {page_url}: {e}")
        return []

def categorize_links(links):
    type_1 = []
    type_2 = []
    
    for link in links:
        if 'xslF345X05' in link:
            type_1.append(link)
        else:
            type_2.append(link)
    
    return type_1, type_2

import requests

def get_company_name(cik):
    cik = str(cik).zfill(10)  # Ensure CIK is 10 digits long
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("name", "Company name not found")
    else:
        return "Invalid CIK or request failed"

def parse_html_form_4(url, cik):
    headers = {"User-Agent": 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            transactions = []
            th_element = soup.find('th', attrs={'class':'FormTextC', 'colspan':'11'})
            non_deriv_table = th_element.find_parent('table')
            if non_deriv_table:
                rows = non_deriv_table.find_all('tr')
                if rows:
                    for row in rows[1:]:
                        columns = row.find_all('td')
                        if len(columns) >= 7:
                            transaction_date = columns[1].text.strip()
                            acquired_disposed = columns[6].text.strip()
                            amount = columns[5].text.strip()
                            price = columns[7].text.strip()
                            transactions.append({
                                'Title': get_company_name(cik),
                                'Transaction Date': transaction_date,
                                'Acquired_Disposed': acquired_disposed,
                                'Amount': amount,
                                'Price': price if price != '$0' else 'N/A'
                            })

            return pd.DataFrame(transactions) if transactions else pd.DataFrame()
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def parse_xml_form_4(url, cik):
    headers = {"User-Agent": 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            transactions = []
            for transaction in root.findall('.//nonDerivativeTransaction'):
                security_title = transaction.find('.//securityTitle/value').text
                amount = transaction.find('.//transactionShares/value').text
                acquired_disposed = transaction.find('.//transactionAcquiredDisposedCode/value').text
                price = transaction.find('.//transactionPricePerShare/value').text if transaction.find('.//transactionPricePerShare/value') is not None else 'N/A'
                transactions.append({
                    'Title': security_title,
                    'Amount': amount,
                    'Acquired_Disposed': acquired_disposed,
                    'Price': price
                })
            return pd.DataFrame(transactions) if transactions else pd.DataFrame()
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Format to run program: python sec_form_4_scraper.py <CIK>")
        sys.exit(1)
    cik = sys.argv[1]
    df = get_form_4_filings(cik)
    if df is not None:
        all_matched_links = []
        for link in df['Link']:
            matched_links = find_wk_form4_links(link, cik)
            # print("matched_links = ", matched_links)
            all_matched_links.extend(matched_links)
        if all_matched_links:
            type_1_links, type_2_links = categorize_links(all_matched_links)
            type_1_dataframes = []
            for link in type_1_links:
                #print("type 1 link = ", link)
                type_1_transactions = parse_html_form_4(link, cik)
                # print("transaction 1 = ", type_1_transactions)
                type_1_dataframes.append(type_1_transactions)
            type_2_dataframes = []
            for link in type_2_links:
                #print("type 2 link = ", link)
                type_2_transactions = parse_xml_form_4(link, cik)
                type_2_dataframes.append(type_2_transactions)
            type_1_df = pd.concat(type_1_dataframes, ignore_index=True) if type_1_dataframes else pd.DataFrame()
            type_2_df = pd.concat(type_2_dataframes, ignore_index=True) if type_2_dataframes else pd.DataFrame()
            final_df = pd.concat([type_1_df, type_2_df], ignore_index=True)
            final_df.to_csv('form_4_filings.csv', index=False)
            print("Data has been saved to form_4_filings.csv")
        else:
            print("No matching links found")
    else:
        print("No data retrieved")