# LLM Security Daily Bot

🤖 Posts 3 unique, recent articles about LLM security to r/LLMSecurity every day.

## 🔷 Setup

1️⃣ Create a Reddit bot account & app at [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → Save client_id, client_secret, username, password.

2️⃣ Clone this repo & create `.env` from `.env.example`.

3️⃣ Test locally:
```bash
pip install -r requirements.txt
python bot.py
```

4️⃣ Deploy to GitHub Actions:
- Add the secrets (`REDDIT_CLIENT_ID`, etc.) to your repo settings → Secrets → Actions.

## 🔷 How it works
- Scrapes Google News & arXiv for recent LLM security articles.
- Deduplicates titles.
- Picks up to 3 unique articles.
- Posts each as a separate link post with flair & disclaimer.

## 📄 License
MIT
