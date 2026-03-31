import os
from playwright.sync_api import sync_playwright  # pyre-ignore
from utils import logger, check_pause_state_sync, get_browser_config  # pyre-ignore

def run_automation(pdf_path="406 Jones Hill Rd.pdf", username=None, password=None):
    with sync_playwright() as p:
        # Launch using centralized configuration
        browser = p.chromium.launch(**get_browser_config())
        context = browser.new_context()
        page = context.new_page()

        logger.info("Navigating to https://qa-pramaan.vercel.app/...")
        page.goto("https://qa-pramaan.vercel.app/")
        
        # Wait for the page to load completely
        page.wait_for_load_state("networkidle")
        
        logger.info(f"Page loaded successfully! Title is: '{page.title()}'")
        
        # -------------------------------------------------------------------
        logger.info("Filling in login credentials...")
        page.get_by_label("Username").fill(username )
        page.get_by_label("Password", exact=False).fill(password)
        
        logger.info("Clicking Log In button...")
        check_pause_state_sync()
        page.get_by_role("button", name="Log In").click()
        
        logger.info("Waiting for Dashboard to load...")
        # Wait longer for the specific review card to be visible in case login is slow
        page.get_by_text("Full File Review").wait_for(state="visible", timeout=30000)
        
        logger.info("Navigating to Full File Review...")
        check_pause_state_sync()
        page.get_by_text("Full File Review").click()
        
        logger.info("Waiting for Full File Review page to load...")
        page.wait_for_load_state("networkidle")
        
        # Add a small delay to see the page
        page.wait_for_timeout(2000)
        
        logger.info(f"Uploading PDF file '{pdf_path}'...")
        check_pause_state_sync()
        page.locator('input[type="file"][accept=".pdf"]').first.set_input_files(pdf_path)
        
        # Wait a bit for the file to process/upload
        page.wait_for_timeout(3000)
        
        logger.info("Pinning the sidebar...")
        page.get_by_label("Pin Sidebar").click()

        def wait_for_spinner(action_name):
            logger.info(f"     Waiting up to 45s for spinner to disappear for {action_name}...")
            spinner = page.locator(".MuiCircularProgress-root, [role='progressbar'], .spinner, .loader").first
            try:
                check_pause_state_sync()
                spinner.wait_for(state="visible", timeout=2000)
            except Exception:
                pass
            try:
                check_pause_state_sync()
                spinner.wait_for(state="hidden", timeout=45000)
            except Exception:
                logger.info(f"     (Timeout or no spinner found for {action_name}, proceeding...)")
            page.wait_for_timeout(1000)

        logger.info("Clicking 'Subject' first to determine Form Type...")
        # Start initial extraction to determine form type and populate the necessary sidebars
        page.locator(".sidebar").get_by_text("Subject", exact=True).click(force=True)
        wait_for_spinner("Subject")

        logger.info("Reading dynamically populated sidebar items for this specific Form Type...")
        # Add a short delay to allow React/MUI to render the new dynamically loaded sidebar items
        page.wait_for_timeout(2000)
        
        # Grab all the visible text inside the sidebar links to form our accurate list
        dynamic_elements = page.locator(".sidebar a.sidebar-link span").all_inner_texts()
        
        # Clean the list (remove empties) and remove 'Subject' since we already extracted it
        dynamic_sidebar_items = [text.strip() for text in dynamic_elements if text.strip() and text.strip() != "Subject"]
        
        logger.info(f"Found {len(dynamic_sidebar_items)} targeted sections for this form: {dynamic_sidebar_items}")
        
        for item in dynamic_sidebar_items:
            logger.info(f"  -> Clicking {item}")
            page.locator(".sidebar").get_by_text(item, exact=True).click(force=True)
            wait_for_spinner(item)
            
        logger.info("Done clicking side bar items.")

        logger.info("Clicking Check State Requirements...")
        page.get_by_role("button", name="Check State Requirements").click()
        wait_for_spinner("Check State Requirements")

        logger.info("Clicking Check Client Requirements...")
        page.get_by_role("button", name="Check Client Requirements").click()
        wait_for_spinner("Check Client Requirements")

        logger.info("Clicking Run Escalation Check...")
        page.get_by_role("button", name="Run Escalation Check").click()
        wait_for_spinner("Run Escalation Check")

        logger.info("Clicking Run Full Analysis...")
        page.get_by_role("button", name="Run Full Analysis").click()
        wait_for_spinner("Run Full Analysis")

        logger.info("Clicking SAVE...")
        page.get_by_role("button", name="SAVE").click()
        page.wait_for_timeout(1000)

        logger.info("Clicking LOG and waiting for download...")
        with page.expect_download() as download_info:
            page.get_by_role("button", name="LOG").click()
        download = download_info.value
        
        # Ensure a dedicated downloads directory exists
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Save the generated file directly to the downloads folder
        save_path = os.path.join(downloads_dir, download.suggested_filename)
        download.save_as(save_path)
        logger.info(f"Log file successfully saved to: {save_path}")

        # -------------------------------------------------------------------
        logger.info("Initiating site logout sequence...")
        try:
            check_pause_state_sync()
            # Standard QA Pramaan logout
            logout_btn = page.get_by_role("button", name="Log Out").first
            if logout_btn.is_visible():
                logout_btn.click()
                page.wait_for_load_state("networkidle")
                logger.success("Securely logged out from the portal.")
        except Exception as e:
            logger.warning(f"Portal logout skipped/failed: {str(e)}")

        page.wait_for_timeout(2000)
        # -------------------------------------------------------------------

        # Close the browser when done
        browser.close()
        
        return save_path

if __name__ == "__main__":
    run_automation()
