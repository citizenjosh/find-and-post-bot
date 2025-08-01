# bot.py
import os
import time
import random
import yaml
import feedparser
import urllib.parse
import re
from dotenv import load_dotenv
from datetime import datetime
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ── Load env & configs ─────────────────────────────────────────────────────────
load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

with open("config.yaml")  as f: config  = yaml.safe_load(f)
with open("sources.yaml") as f: sources = yaml.safe_load(f)

SUBREDDIT    = config["subreddit"]
MAX_POSTS    = config["max_posts"]
DISCLAIMER   = config["disclaimer"]
FLAIR_MAP    = config.get("flairs", {})
PROMPT       = config["prompt_template"]

# ── Helpers ─────────────────────────────────────────────────────────────────────
def strip_html(text):  
    return re.sub(r"<[^>]+>", "", text).strip()

def summarize_with_gpt(text):
    prompt = PROMPT.format(content=text)
    try:
        r = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=150, temperature=0.3
        )
        return strip_html(r.choices[0].message.content)
    except Exception as e:
        print("GPT error:", e)
        return text

def type_like_human(elem, text):
    for c in text:
        elem.send_keys(c)
        time.sleep(random.uniform(0.05, 0.18))

# ── Fetchers (unchanged) ────────────────────────────────────────────────────────
def extract_original_url(u):
    p = urllib.parse.urlparse(u)
    q = urllib.parse.parse_qs(p.query)
    return q.get("url",[u])[0]

def fetch_rss(src):
    feed = feedparser.parse(src["url"])
    out = []
    for e in feed.entries:
        link = extract_original_url(e.link) if src["type"]=="news" else e.link
        out.append({
            "title":   e.title.strip(),
            "summary": strip_html(getattr(e,"summary","")),
            "link":    link,
            "source":  src["name"],
        })
    return out

def fetch_reddit_search(src):
    q     = src["query"]
    tf    = src.get("time_filter","day")
    excl  = {s.lower() for s in src.get("exclude_subreddits",[])}
    out   = []
    for sub in reddit.subreddit("all").search(q,sort="new",time_filter=tf,limit=10):
        if sub.subreddit.display_name.lower() in excl: continue
        out.append({
            "title":   sub.title,
            "summary": strip_html(sub.selftext or sub.title),
            "link":    f"https://reddit.com{sub.permalink}",
            "source":  src["name"],
        })
    return out

def collect_all():
    items = []
    for s in sources:
        if s["type"] in ("news","research"):
            items += fetch_rss(s)
        elif s["type"]=="reddit-search":
            items += fetch_reddit_search(s)
    return items

def dedupe(items):
    seen, out = set(), []
    for i in items:
        k=i["title"].lower().strip()
        if k not in seen:
            seen.add(k); out.append(i)
    return out

# ── Selenium Uploader ────────────────────────────────────────────────────────────
def post_via_ui(article):
    # 1) Launch headless Chrome under Xvfb
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    driver = webdriver.Chrome(service=ChromeDriverManager().install(), options=opts)

    # 2) Go to Reddit submit page for text post
    driver.get(f"https://www.reddit.com/r/{SUBREDDIT}/submit/?type=self")

    time.sleep(3)  # wait for page & login
    
    # 3) Fill Title
    title_el = driver.find_element(By.CSS_SELECTOR, "textarea[name='title']")
    type_like_human(title_el, article["title"])

    # 4) Fill Body
    body_el = driver.find_element(By.CSS_SELECTOR, "div[role='textbox']")
    summary = summarize_with_gpt(article["summary"])
    body_text = f"[Read more]({article['link']})\n\n{summary}\n\n{DISCLAIMER}"
    type_like_human(body_el, body_text)

    # 5) (Optional) set flair
    flair_text = FLAIR_MAP.get(article["source"])
    if flair_text:
        # open flair menu
        driver.find_element(By.CSS_SELECTOR, "button[id*='PostFlair']").click()
        time.sleep(1)
        # select by visible text
        flair_el = driver.find_element(By.XPATH, f"//span[text()='{flair_text}']")
        flair_el.click()

    time.sleep(1)
    # 6) Submit
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()

    print("✅ posted via UI:", article["title"])
    driver.quit()

# ── Main ────────────────────────────────────────────────────────────────────────
if __name__=="__main__":
    print("--- Running at", datetime.utcnow(), "UTC ---")
    all_items = dedupe(collect_all())[:MAX_POSTS]
    for art in all_items:
        post_via_ui(art)
    print("--- Done ---")
