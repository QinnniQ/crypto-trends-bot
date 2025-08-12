import os
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain.schema import Document

# === LOAD ENV ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env")

# === CONFIG ===
CHROMA_DB_DIR = r"C:\Users\nicho\Documents\crypto_bot\chroma_db"

# ✅ Correct Substack domains
SUBSTACK_SITES = [
    "https://bankless.substack.com/",
    "https://coinbureau.substack.com/"
]

# === INIT ===
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", api_key=OPENAI_API_KEY)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
db = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)

# === GET LATEST POST LINKS ===
def get_recent_post_links(homepage_url, limit=5):
    """Scrape homepage and return list of latest post URLs."""
    links = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(homepage_url, timeout=60000)

        # Scroll to load posts
        for _ in range(3):
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(2000)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/p/" in href:  # Substack article URL pattern
            if href.startswith("/"):
                href = homepage_url.rstrip("/") + href
            if href not in links:
                links.append(href)
    return links[:limit]

# === FETCH FULL ARTICLE ===
def fetch_full_article(url):
    """Fetch full article text via Playwright."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        article_container = soup.find("article") or soup.find("div", {"role": "main"})
        if article_container:
            return article_container.get_text(separator=" ", strip=True)
        return soup.get_text(separator=" ", strip=True)

    except Exception as e:
        print(f"⚠ Error fetching article: {url} | {e}")
        return ""

# === INGEST ===
def ingest():
    all_docs = []
    for site in SUBSTACK_SITES:
        print(f"📡 Scraping homepage: {site}")
        post_links = get_recent_post_links(site)
        print(f"🔗 Found {len(post_links)} recent posts.")

        for link in post_links:
            text = fetch_full_article(link)
            print(f"\n📰 {link}")
            print(f"📏 Length: {len(text)} chars")
            print(f"📄 Preview: {text[:300]}...\n")

            if len(text) > 200:
                chunks = text_splitter.split_text(text)
                for chunk in chunks:
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            "source": "substack",
                            "title": link.split("/")[-1],
                            "url": link,
                            "date": datetime.utcnow().strftime("%Y-%m-%d"),
                            "ingest_date": datetime.utcnow().strftime("%Y-%m-%d")
                        }
                    )
                    all_docs.append(doc)

    if all_docs:
        print(f"📦 Ingesting {len(all_docs)} chunks into ChromaDB...")
        db.add_documents(all_docs)
        db.persist()
        print("✅ Substack ingestion complete.")
    else:
        print("⚠ No new documents found.")

if __name__ == "__main__":
    ingest()
