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
        page.wait_for_timeout(2000)
        
        file_inputs = page.locator('input[type="file"]')
        count = file_inputs.count()
        print(f'Total file inputs found: {count}')
        for i in range(count):
            print(f'Input {i}')
        
        html = page.content()
        with open('page_dump.html', 'w', encoding='utf-8') as f:
            f.write(html)
        browser.close()

if __name__ == '__main__':
    inspect()
