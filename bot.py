import os
import re
import yaml
import praw
import feedparser
import urllib.parse
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

# ── Load secrets & configs ────────────────────────────────────────────────────
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

with open("config.yaml") as f:
    config = yaml.safe_load(f)

with open("sources.yaml") as f:
    sources = yaml.safe_load(f)

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("USER_AGENT"),
)

SUBREDDIT    = config["subreddit"]
MAX_POSTS    = config["max_posts"]
DISCLAIMER   = config["disclaimer"]
FLAIR_MAP    = config["flairs"]
PROMPT       = config["prompt_template"]


# ── Helpers ─────────────────────────────────────────────────────────────────────
def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()

def summarize_with_gpt(text: str) -> str:
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content": PROMPT.format(content=text)}],
            max_tokens=150,
            temperature=0.3,
        )
        return strip_html(resp.choices[0].message.content)
    except Exception as e:
        print("GPT error:", e)
        return text

def post_to_reddit(item: dict):
    sr = reddit.subreddit(SUBREDDIT)
    summary = summarize_with_gpt(item["summary"])
    body    = f"[Read more]({item['link']})\n\n{summary}\n\n{DISCLAIMER}"
    submission = sr.submit(title=item["title"], selftext=body)
    flair_name = FLAIR_MAP.get(item["source"])
    if flair_name:
        for template in sr.flair.link_templates:
            if template["text"] == flair_name:
                submission.flair.select(template["id"])
                break
    print("✅", item["title"])

# ── Source Fetchers ─────────────────────────────────────────────────────────────
def fetch_rss(source: dict) -> list:
    feed = feedparser.parse(source["url"])
    items = []
    for e in feed.entries:
        link = e.link
        if source["type"] == "news":  # strip Google’s redirect if present
            q = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
            link = q.get("url", [link])[0]
        items.append({
            "title":   e.title.strip(),
            "summary": strip_html(getattr(e, "summary", "")),
            "link":    link,
            "source":  source["name"],
        })
    return items

def fetch_reddit_search(source: dict) -> list:
    q     = source["query"]
    tf    = source.get("time_filter", "day")
    excl  = {s.lower() for s in source.get("exclude_subreddits", [])}
    items = []
    for sub in reddit.subreddit(source.get("subreddit","all")) \
                     .search(q, sort="new", time_filter=tf, limit=10):
        if sub.subreddit.display_name.lower() in excl:
            continue
        items.append({
            "title":   sub.title,
            "summary": strip_html(sub.selftext or sub.title),
            "link":    f"https://reddit.com{sub.permalink}",
            "source":  source["name"],
        })
    return items

# ── Core Loop ──────────────────────────────────────────────────────────────────
def main():
    print(f"--- Running at {datetime.utcnow()} UTC ---")
    collected = []

    for src in sources:
        typ = src["type"]
        if typ in ("news","research"):
            collected += fetch_rss(src)
        elif typ == "reddit-search":
            collected += fetch_reddit_search(src)

    # dedupe by title
    seen, unique = set(), []
    for item in collected:
        key = item["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    for article in unique[:MAX_POSTS]:
        post_to_reddit(article)

    print("--- Done ---")

if __name__ == "__main__":
    main()
