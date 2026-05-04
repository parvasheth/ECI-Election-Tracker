import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup

def setup_sheets():
    print("[+] Connecting to Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'service_account.json')
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    # The sheet ID provided by the user
    sheet = client.open_by_key("1mTnwDbsvtq0WcKsfgjJALY8ajoGM_ZOAD72yTmZcGmM").sheet1
    return sheet

def scrape_eci_data(context):
    all_data = []
    # Hardcode expected headers to avoid colspan/multirow header issues
    headers = ['Constituency', 'Const. No.', 'Leading Candidate', 'Leading Party', 'Trailing Candidate', 'Trailing Party', 'Margin', 'Round', 'Status']
    
    page = context.new_page()
    
    # Loop over possible pages (up to 30)
    for page_num in range(1, 30):
        url = f"https://results.eci.gov.in/ResultAcGenMay2026/statewiseS25{page_num}.htm"
        print(f"[*] Fetching page {page_num}: {url}")
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(1) # Give it a moment to render
            
            if not page.query_selector("table"):
                print(f"[-] No table found on page {page_num}. Assuming we reached the end.")
                break
                
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find the main table
            main_table = None
            for t in soup.find_all('table'):
                th_text = " ".join([th.text for th in t.find_all('th')])
                if "Constituency" in th_text and "Leading Candidate" in th_text:
                    main_table = t
                    break
                    
            if not main_table:
                break
                
            # Get only direct rows of tbody or table to avoid nested tooltips
            tbody = main_table.find('tbody')
            rows = tbody.find_all('tr', recursive=False) if tbody else main_table.find_all('tr', recursive=False)
            
            for row in rows:
                cols = row.find_all(['td', 'th'], recursive=False)
                if cols and len(cols) >= 9:
                    # Clean tooltip junk "iParty Wise State Trends..."
                    col_data = []
                    for col in cols[:9]:
                        val = col.text.strip().replace('\n', ' ')
                        # Remove the hidden tooltip data
                        if 'iParty' in val:
                            val = val.split('iParty')[0].strip()
                        col_data.append(val)
                    
                    # Only add if it's not a header row masquerading as data
                    if col_data[0] != 'Constituency':
                        all_data.append(col_data)
                    
        except Exception as e:
            print(f"[-] Error fetching page {page_num}: {e}")
            break
            
    page.close()
    return headers, all_data

def scrape_vote_share(context):
    url = "https://results.eci.gov.in/ResultAcGenMay2026/voteshareresult-S25.htm"
    print(f"[*] Fetching Vote Share from: {url}")
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    time.sleep(1)
    
    content = page.content()
    soup = BeautifulSoup(content, 'html.parser')
    table = soup.find('table')
    
    headers = ['Party', 'Vote %', 'Total Votes']
    all_data = []
    
    if table:
        rows = table.find_all('tr')
        for r in rows[1:]: # Skip header row
            cols = [c.text.strip() for c in r.find_all(['td'])]
            if len(cols) >= 4:
                # Format: ['', 'AITC', '41.51%', '6603239']
                all_data.append([cols[1], cols[2].replace('%', ''), cols[3]])
                
    page.close()
    return headers, all_data

def main():
    sheet = setup_sheets()
    
    with sync_playwright() as p:
        print("[+] Launching browser to bypass protections...")
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800}, 
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        headers, all_data = scrape_eci_data(context)
        vs_headers, vs_data = scrape_vote_share(context)
        
        browser.close()
    
    if all_data:
        print(f"[+] Successfully scraped {len(all_data)} rows of data.")
        print("[+] Updating Google Sheet...")
        
        # Clear existing data
        sheet.clear()
        
        max_cols = len(headers)
        cleaned_data = []
        for row in all_data:
            if len(row) > max_cols:
                row = row[:max_cols]
            elif len(row) < max_cols:
                row = row + [""] * (max_cols - len(row))
            cleaned_data.append(row)
            
        # Write to sheets
        sheet.append_rows([headers] + cleaned_data, value_input_option="USER_ENTERED")
        print("[+] Seat Data Google Sheet updated successfully!")
    else:
        print("[-] No data scraped. Check if the site structure has changed or if we are being blocked.")

    # Write vote share data
    if vs_data:
        print(f"[+] Successfully scraped {len(vs_data)} rows of vote share data.")
        client = sheet.client
        spreadsheet = client.open_by_key("1mTnwDbsvtq0WcKsfgjJALY8ajoGM_ZOAD72yTmZcGmM")
        try:
            vs_sheet = spreadsheet.worksheet("Vote_Share")
        except gspread.exceptions.WorksheetNotFound:
            vs_sheet = spreadsheet.add_worksheet(title="Vote_Share", rows="100", cols="5")
            
        vs_sheet.clear()
        vs_sheet.append_rows([vs_headers] + vs_data, value_input_option="USER_ENTERED")
        print("[+] Vote Share Google Sheet updated successfully!")

if __name__ == "__main__":
    main()
