from playwright.sync_api import sync_playwright

def inspect():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://qa-pramaan.vercel.app/')
        page.wait_for_load_state('networkidle')
        page.get_by_label('Username').fill('Abhi')
        page.get_by_label('Password', exact=False).fill('Admin@2026')
        page.get_by_role('button', name='Log In').click()
        page.get_by_text('Revised File Review').wait_for(state='visible', timeout=15000)
        page.get_by_text('Revised File Review').click()
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        
        # Check specific locators
        try:
            old_input = page.locator('div:has-text("Old File") input[type="file"], div:has-text("Old Report") input[type="file"]')
            print("Old file count:", old_input.count())
        except Exception as e:
            print(e)
            
        print("--- ALL FILE INPUTS WITH PARENTS ---")
        inputs = page.locator('input[type="file"]')
        for i in range(inputs.count()):
            accept = inputs.nth(i).get_attribute('accept')
            parent_text = inputs.nth(i).locator('xpath=..').inner_text()
            print(f"Input {i}: accept={accept}, text={parent_text.strip()}")
            
        browser.close()

if __name__ == '__main__':
    inspect()
