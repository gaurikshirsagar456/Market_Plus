import os
import httpx
from dotenv import load_dotenv

load_dotenv()  # Load .env file
NEWS_KEY = os.getenv("NEWSAPI_KEY")  # ✅ Correct

async def get_latest_news(ticker: str):
    """
    Fetch 5 latest news headlines about the ticker using NewsAPI
    """
    query = f"{ticker} stock OR {ticker} company"
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_KEY}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()

    # Debugging: check API response
    if "articles" not in data:
        print("NEWSAPI ERROR:", data)
        return []

    articles = data["articles"][:5]
    return [
        {
            "title": a["title"],
            "description": a["description"],
            "url": a["url"]
        }
        for a in articles
    ]
