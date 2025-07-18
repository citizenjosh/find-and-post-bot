
# LLM Security Daily Bot (AI-enhanced)

🤖 Posts 3 unique, recent articles about LLM security to r/LLMSecurity every day, using GPT-3.5 to generate polished summaries.

## 🔷 Setup

1️⃣ Create a Reddit bot account & app at [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → Save client_id, client_secret, username, password.  
2️⃣ Get an OpenAI API key at https://platform.openai.com/account/api-keys with **write: /v1/chat/completions** permission.  
3️⃣ Clone this repo & create `.env` from `.env.example` with your secrets.

## 🔷 Local test

```bash
pip install -r requirements.txt
python bot.py
```

## 🔷 GitHub Actions

- Add the secrets (`REDDIT_CLIENT_ID`, `OPENAI_API_KEY`, etc.) to your repo Settings → Secrets → Actions.
- Push the code — it runs daily at 12:00 UTC or manually via Actions.

## 🔷 What it does

✅ Scrapes Google News & arXiv for recent LLM security articles.  
✅ Deduplicates titles.  
✅ Uses GPT-3.5 to write clear summaries.  
✅ Posts as text posts (self-posts) with link, summary & disclaimer.  
✅ Adds flair.  

---

MIT License.
