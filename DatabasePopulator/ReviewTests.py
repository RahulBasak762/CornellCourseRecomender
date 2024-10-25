from playwright.sync_api import sync_playwright

    # Initialize Playwright
with sync_playwright() as p:
    overallRating = [-1.0, -1.0, -1.0]

    try:
        browser = p.chromium.launch(headless=True)

        # Open a new page
        page = browser.new_page()

        # Navigate to the website
        page.goto("https://www.cureviews.org/course/CS/3700")

        # Wait for the rating element to load (adjust selector based on actual HTML)
        page.wait_for_selector("._rating_zvrrc_22", timeout=1000)
        # Extract the rating
        overallRating = page.query_selector_all("._rating_zvrrc_22")

        for i in range(3):
            overallRating[i] = float(overallRating[i].text_content().strip())
    except Exception as e:
        overallRating = [-1.0, -1.0, -1.0]
    finally:
        # Close the browser
        browser.close()

    print(overallRating)




