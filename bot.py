import os
import praw
import requests
import feedparser
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
USER_AGENT = os.getenv("USER_AGENT")
SUBREDDIT = "llmsecurity"
MAX_POSTS = 3
DISCLAIMER = "*Automated post. Please discuss below.*"

FLAIR_MAP = {
    "news": "News",
    "research": "Research"
}

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=USER_AGENT
)

def fetch_google_news():
    url = "https://news.google.com/rss/search?q=LLM+security+OR+%22large+language+model%22+security&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        articles.append({
            'title': entry.title,
            'link': entry.link,
            'summary': entry.summary,
            'source': 'news'
        })
    return articles

def fetch_arxiv():
    url = "http://export.arxiv.org/api/query?search_query=all:large+language+model+security&start=0&max_results=5&sortBy=lastUpdatedDate&sortOrder=descending"
    feed = feedparser.parse(url)
    papers = []
    for entry in feed.entries:
        papers.append({
            'title': entry.title.replace('\n', ' ').strip(),
            'link': entry.link,
            'summary': entry.summary.replace('\n', ' ').strip(),
            'source': 'research'
        })
    return papers

def deduplicate(articles):
    unique = []
    seen_titles = set()
    for art in articles:
        title_key = art['title'].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique.append(art)
    return unique

def post_to_reddit(article):
    subreddit = reddit.subreddit(SUBREDDIT)
    flair = FLAIR_MAP.get(article['source'], None)
    title = f"{article['title']}"
    submission = subreddit.submit(title=title, url=article['link'], resubmit=False)

    if flair:
        flair_id = None
        for f in subreddit.flair.link_templates:
            if f['text'] == flair:
                flair_id = f['id']
                break
        if flair_id:
            submission.flair.select(flair_id)

    print(f"Posted: {title}")

if __name__ == "__main__":
    print(f"\n--- Running bot at {datetime.utcnow()} UTC ---")
    news = fetch_google_news()
    research = fetch_arxiv()
    combined = deduplicate(news + research)
    if not combined:
        print("No unique articles found today. Skipping.")
    else:
        for article in combined[:MAX_POSTS]:
            post_to_reddit(article)
    print("--- Done ---")
