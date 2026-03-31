import re
import difflib
from bs4 import BeautifulSoup

# Load the saved HTML file
html_path = r"c:\Users\Admin\.gemini\antigravity\scratch\qa-pramaan-automation\Downloads\HTMLFiles\263-03500.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')

def test_locator_logic():
    print("Testing Updated Locator Logic on saved HTML...")
    
    # Updated logic: Search for tables with 'Document Type' header that are NOT hidden
    # In BeautifulSoup, we can't check 'visible' easily, but we can look for the ID 'ctl00_cphBody_grdDocs'
    # which we found is the visible one.
    
    # 1. Find all tables with 'Document Type' header
    tables = soup.find_all('table')
    relevant_tables = []
    for t in tables:
        if t.find('th', string=re.compile(r'Document Type')):
            relevant_tables.append(t)
    
    print(f"Found {len(relevant_tables)} tables with 'Document Type' header.")
    
    # 2. Identify the tables
    for i, t in enumerate(relevant_tables):
        t_id = t.get('id', 'No ID')
        parent_div = t.find_parent('div', id=True)
        parent_id = parent_div.get('id', 'No Parent ID') if parent_div else "No Parent Div"
        print(f"Table {i+1}: ID={t_id}, Parent ID={parent_id}")
        
        # Check links in this table
        links = t.find_all('a', string=re.compile(r'\.pdf', re.IGNORECASE))
        print(f"  -> Found {len(links)} PDF links.")
        for link in links:
            print(f"     - Link: {link.text.strip()}")

    # Simulate the Playwright selector: #ctl00_cphBody_grdDocs
    target_table = soup.find('table', id='ctl00_cphBody_grdDocs')
    if target_table:
        print("\nSUCCESS: Target table 'ctl00_cphBody_grdDocs' found!")
        links = target_table.find_all('a', string=re.compile(r'\.pdf', re.IGNORECASE))
        print(f"Links in target table: {[l.text.strip() for l in links]}")
        
        # Test similarity matching
        revised_base_name = "408 mitchell ave"
        print(f"\nTesting matching for: '{revised_base_name}'")
        for link in links:
            raw_text = link.text.strip()
            link_text = raw_text.lower().replace('.pdf', '').replace('.xml', '').strip()
            similarity = difflib.SequenceMatcher(None, revised_base_name, link_text).ratio()
            print(f"Checking link: '{raw_text}' (Similarity: {similarity:.2f})")
            if similarity >= 0.6 or revised_base_name in link_text or link_text in revised_base_name:
                print(f"✅ MATCH FOUND: {raw_text}")

if __name__ == "__main__":
    test_locator_logic()
