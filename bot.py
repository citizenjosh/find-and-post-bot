import os
import praw
import openai
import feedparser
import urllib.parse
import re
import yaml
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load config files
def load_yaml(file_path):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

config = load_yaml("config.yaml")
sources = load_yaml("sources.yaml")

# Load environment secrets
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
USER_AGENT = os.getenv("USER_AGENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=USER_AGENT
)

def extract_original_url(google_news_url):
    parsed = urllib.parse.urlparse(google_news_url)
    query = urllib.parse.parse_qs(parsed.query)
    if 'url' in query:
        return query['url'][0]
    return google_news_url

def strip_html(text):
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'&[a-z]+;', '', text)
    return text.strip()

def fetch_feed(feed_config):
    if not feed_config.get("enabled", True):
        return []

    url_template = feed_config["rss_url"]
    query = urllib.parse.quote_plus(feed_config.get("query", ""))
    feed_url = url_template.format(query=query)

    feed = feedparser.parse(feed_url)
    articles = []
    for entry in feed.entries:
        clean_link = extract_original_url(entry.link)
        clean_summary = strip_html(entry.summary.replace('\n', ' '))
        articles.append({
            'title': entry.title.replace('\n', ' ').strip(),
            'link': clean_link,
            'summary': clean_summary,
            'source': feed_config["type"]
        })
    return articles

def deduplicate(articles):
    unique = []
    seen_titles = set()
    for art in articles:
        key = art['title'].lower().strip()
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(art)
    return unique

def summarize_with_gpt(text):
    prompt = config["prompt_template"].replace("{content}", text)
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
    subreddit = reddit.subreddit(config["subreddit"])
    flair = config["flairs"].get(article['source'], None)

    gpt_summary = summarize_with_gpt(article['summary'])

    title = article['title']
    body = f"[Read the article here]({article['link']})\n\n{gpt_summary}\n\n{config['disclaimer']}"

    submission = subreddit.submit(title=title, selftext=body)

    if flair:
        for f in subreddit.flair.link_templates:
            if f['text'] == flair:
                submission.flair.select(f['id'])
                break

def main():
    print(f"--- Running bot at {datetime.utcnow()} UTC ---")
    all_articles = []

    for name, feed_conf in sources.items():
        print(f"Fetching from: {name}")
        articles = fetch_feed(feed_conf)
        all_articles.extend(articles)

    articles = deduplicate(all_articles)[:config["max_posts"]]

    for art in articles:
        post_to_reddit(art)
        print(f"✅ Posted: {art['title']}")
    print("--- Done ---")

if __name__ == "__main__":
    main()
