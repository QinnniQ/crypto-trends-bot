import os
import json
import time
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def extract_post_content(driver, url):
    driver.get(url)
    time.sleep(3)  # Wait for page to fully load

    soup = BeautifulSoup(driver.page_source, "html.parser")

    article_tag = soup.find("article")
    if not article_tag:
        return None  # Skip if article not found

    title = soup.title.string.strip() if soup.title else "Untitled"
    paragraphs = article_tag.find_all("p")
    body = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    date_tag = soup.find("time")
    date = date_tag.get("datetime", "") if date_tag else ""

    return {
        "title": title,
        "url": url,
        "date": date,
        "content": body
    }

def scrape_all_articles(input_file="substack_links.json", output_dir="articles"):
    Path(output_dir).mkdir(exist_ok=True)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    with open(input_file, "r", encoding="utf-8") as f:
        all_links = json.load(f)

    total_count = 0
    for source, posts in all_links.items():
        for post in posts:
            url = post["url"]
            print(f"🔍 Scraping: {url}")
            try:
                article_data = extract_post_content(driver, url)
                if article_data:
                    article_data["source"] = source
                    fname = f"{source}_{total_count:03d}.json"
                    with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as out:
                        json.dump(article_data, out, ensure_ascii=False, indent=2)
                    print(f"✅ Saved: {fname}")
                    total_count += 1
                else:
                    print("⚠️ No article content found.")
            except Exception as e:
                print(f"❌ Failed to scrape {url}: {e}")

    driver.quit()
    print(f"\n🎉 Finished scraping {total_count} articles.")

if __name__ == "__main__":
    scrape_all_articles()
