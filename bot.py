import os
import praw
import openai
import feedparser
import urllib.parse
import re
import yaml
from datetime import datetime
from dotenv import load_dotenv

# Load env vars
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load configs
with open("config.yaml") as f:
    config = yaml.safe_load(f)

with open("sources.yaml") as f:
    sources = yaml.safe_load(f)

# Reddit client
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("USER_AGENT"),
)

SUBREDDIT = config["subreddit"]
MAX_POSTS = config["max_posts"]
DISCLAIMER = config["disclaimer"]
FLAIR_MAP = config.get("flairs", {})
PROMPT = config["prompt_template"]

def strip_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()

def summarize(text):
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": PROMPT.format(content=text)}],
            max_tokens=150,
            temperature=0.3,
        )
        return strip_html(resp.choices[0].message.content)
    except Exception as e:
        print("GPT error:", e)
        return text

def fetch_rss(source):
    """Generic RSS fetch for type 'news' or 'research'."""
    feed = feedparser.parse(source["url"])
    items = []
    for e in feed.entries:
        # extract original URL if Google News redirect
        link = e.link
        if source["type"] == "news":
            parsed = urllib.parse.urlparse(link)
            q = urllib.parse.parse_qs(parsed.query)
            link = q.get("url", [link])[0]
        items.append({
            "title": e.title.strip(),
            "summary": strip_html(getattr(e, "summary", "")),
            "link": link,
            "source": source["name"],
        })
    return items

def fetch_reddit_search(source):
    """Fetch Reddit submissions by search."""
    q = source["query"]
    tf = source.get("time_filter", "day")
    excl = {s.lower() for s in source.get("exclude_subreddits", [])}
    items = []
    for sub in reddit.subreddit(source.get("subreddit","all")) \
                     .search(q, sort="new", time_filter=tf, limit=10):
        if sub.subreddit.display_name.lower() in excl:
            continue
        items.append({
            "title": sub.title,
            "summary": strip_html(sub.selftext or sub.title),
            "link": f"https://www.reddit.com{sub.permalink}",
            "source": source["name"],
        })
    return items

def collect_all():
    all_items = []
    for src in sources:
        t = src["type"]
        if t in ("news","research"):
            all_items += fetch_rss(src)
        elif t == "reddit-search":
            all_items += fetch_reddit_search(src)
    return all_items

def dedupe(items):
    seen = set(); uniq = []
    for it in items:
        k = it["title"].lower()
        if k not in seen:
            seen.add(k); uniq.append(it)
    return uniq

def post(item):
    sr = reddit.subreddit(SUBREDDIT)
    summary = summarize(item["summary"])
    body = f"[Read more]({item['link']})\n\n{summary}\n\n{DISCLAIMER}"
    post = sr.submit(title=item["title"], selftext=body)
    flair = FLAIR_MAP.get(item["source"])
    if flair:
        for f in sr.flair.link_templates:
            if f["text"] == flair:
                post.flair.select(f["id"])
                break
    print("✅", item["title"])

if __name__ == "__main__":
    print("--- Running at", datetime.utcnow(), "UTC ---")
    articles = dedupe(collect_all())[:MAX_POSTS]
    for art in articles:
        post(art)
    print("--- Done ---")

