import re
import difflib
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Login
        logger.info("Navigating to login page...")
        page.goto("https://fastapp.spurams.com/login.aspx")
        page.fill("input#ctl00_cphBody_Login1_UserName", "")
        page.fill("input#ctl00_cphBody_Login1_Password", "")
        page.click("input#ctl00_cphBody_Login1_LoginButton")
        
        # Wait and capture state
        page.wait_for_timeout(5000)
        page.screenshot(path="tmp/login_attempt.png")
        logger.info(f"URL after login attempt: {page.url}")
        
        if "AppraiserDashboard.aspx" not in page.url:
            logger.error("Login failed. Check tmp/login_attempt.png")
            return

        # Wait for dashboard
        page.wait_for_selector("#ctl00_lblUserFullName")
        logger.info("Logged in successfully.")
        
        # Go to a specific appraisal that I know has multiple docs
        # Using ApprID 200733 from the HTML I read earlier
        appr_id = "200733"
        url = f"https://fastapp.spurams.com/ViewAppraisal.aspx?ApprID={appr_id}"
        logger.info(f"Navigating to appraisal: {url}")
        page.goto(url)
        
        # Test the locator logic
        # 1. Old logic (should find the hidden table)
        old_table = page.locator("table").filter(has=page.locator("th:has-text('Document Type')")).first
        old_table_id = old_table.get_attribute("id")
        logger.info(f"Old logic table ID: {old_table_id}")
        
        # 2. New logic (should find the visible table)
        new_table = page.locator("#ctl00_cphBody_grdDocs, table:has(th:has-text('Document Type')):visible").first
        new_table_id = new_table.get_attribute("id")
        logger.info(f"New logic table ID: {new_table_id}")
        
        # Check links
        revised_base_name = "408 mitchell ave" # From the log
        links = new_table.locator("a").filter(has_text=re.compile(r'\.pdf', re.IGNORECASE))
        link_count = links.count()
        logger.info(f"Found {link_count} potential PDF links in the visible table.")
        
        for i in range(link_count):
            link = links.nth(i)
            raw_text = link.inner_text().strip()
            link_text = raw_text.lower().replace('.pdf', '').replace('.xml', '').strip()
            similarity = difflib.SequenceMatcher(None, revised_base_name, link_text).ratio()
            logger.info(f"Checking link: '{raw_text}' (Similarity: {similarity:.2f})")
            if similarity >= 0.6 or revised_base_name in link_text or link_text in revised_base_name:
                logger.info(f"✅ MATCH: {raw_text}")

        browser.close()

if __name__ == "__main__":
    verify()
