import os
import praw
import openai
import feedparser
import urllib.parse
import re
from datetime import datetime
from dotenv import load_dotenv

# Load env variables
load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
USER_AGENT = os.getenv("USER_AGENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Constants
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


def extract_original_url(google_news_url):
    """Extract original URL from Google News redirect."""
    parsed = urllib.parse.urlparse(google_news_url)
    query = urllib.parse.parse_qs(parsed.query)
    if 'url' in query:
        return query['url'][0]
    return google_news_url


def strip_html(text):
    """Remove HTML tags and decode basic entities."""
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'&[a-z]+;', '', text)
    return text.strip()


def fetch_google_news():
    url = "https://news.google.com/rss/search?q=LLM+security+OR+%22large+language+model%22+security&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        clean_link = extract_original_url(entry.link)
        clean_summary = strip_html(entry.summary)
        articles.append({
            'title': entry.title,
            'link': clean_link,
            'summary': clean_summary,
            'source': 'news'
        })
    return articles


def fetch_arxiv():
    url = "http://export.arxiv.org/api/query?search_query=all:large+language+model+security&start=0&max_results=5&sortBy=lastUpdatedDate&sortOrder=descending"
    feed = feedparser.parse(url)
    papers = []
    for entry in feed.entries:
        clean_summary = strip_html(entry.summary.replace('\n', ' '))
        papers.append({
            'title': entry.title.replace('\n', ' ').strip(),
            'link': entry.link,
            'summary': clean_summary,
            'source': 'research'
        })
    return papers


def deduplicate(articles):
    """Deduplicate based on lowercase title."""
    unique = []
    seen_titles = set()
    for art in articles:
        key = art['title'].lower().strip()
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(art)
    return unique


def summarize_with_gpt(text):
    """Use GPT to generate a clean, concise summary."""
    prompt = (
        "Summarize the following text into 1–2 clear, concise sentences suitable for a Reddit post, "
        "highlighting why it’s relevant to large language model (LLM) security:\n\n"
        f"{text}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        summary = response.choices[0].message.content.strip()
        return strip_html(summary)
    except Exception as e:
        print(f"Error summarizing with GPT: {e}")
        return text


def post_to_reddit(article):
    subreddit = reddit.subreddit(SUBREDDIT)
    flair = FLAIR_MAP.get(article['source'], None)

    # Clean and summarize
    summary_text = strip_html(article['summary'])
    gpt_summary = summarize_with_gpt(summary_text)

    title = article['title']
    body = f"[Read the article here]({article['link']})\n\n{gpt_summary}\n\n{DISCLAIMER}"

    submission = subreddit.submit(title=title, selftext=body)

    if flair:
        for f in subreddit.flair.link_templates:
            if f['te]()
