from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

def scrape_substack_homepage(url, max_scrolls=15):
    options = Options()
    options.add_argument("--headless")  # Comment this to see the browser
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(3)

    # Scroll to load more posts
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    # Extract links
    links = driver.find_elements(By.TAG_NAME, "a")
    seen = set()
    posts = []

    for link in links:
        href = link.get_attribute("href")
        title = link.text.strip()
        if (
            href
            and "/p/" in href  # Substack posts use this pattern
            and href not in seen
            and title
        ):
            seen.add(href)
            posts.append({"title": title, "url": href})

    driver.quit()
    return posts

if __name__ == "__main__":
    newsletters = {
        "rektcapital": "https://rektcapital.substack.com/",
        "unchainedcrypto": "https://unchainedcrypto.substack.com/",
        "cryptoquant": "https://cryptoquant.substack.com/"
    }

    all_links = {}
    for name, url in newsletters.items():
        print(f"🌐 Scraping {name}...")
        posts = scrape_substack_homepage(url)
        print(f"✅ Found {len(posts)} posts for {name}")
        all_links[name] = posts

    with open("substack_links.json", "w", encoding="utf-8") as f:
        json.dump(all_links, f, indent=2, ensure_ascii=False)

    print("💾 Saved post links to substack_links.json")
