from playwright.sync_api import sync_playwright

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Dashboard
        page.goto("http://localhost:9999/")
        page.screenshot(path="dashboard.png")

        # Sites list
        page.goto("http://localhost:9999/sites")
        page.screenshot(path="sites.png")

        # Add site page
        page.goto("http://localhost:9999/add-site")
        page.screenshot(path="add_site.png")



        browser.close()

if __name__ == "__main__":
    run_verification()
