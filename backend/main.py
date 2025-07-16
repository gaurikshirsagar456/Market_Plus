from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from services.price_service import get_price_momentum
from services.news_service import get_latest_news
from services.llm_service import analyze_pulse, summarize_news_sentiment

app = FastAPI(title="Market Pulse API")

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/market-pulse")
async def market_pulse(ticker: str = Query(..., min_length=1)):
    # ✅ Get last 5-day momentum
    momentum_data = await get_price_momentum(ticker)

    # ✅ Get latest news
    news_data = await get_latest_news(ticker)

    # ✅ Compute sentiment summary
    avg_score, sentiment_label, sentiment_summary = summarize_news_sentiment(news_data)

    # ✅ Get pulse + explanation
    llm_result = await analyze_pulse(ticker, momentum_data, news_data)
    pulse = llm_result.get("pulse", "neutral")
    explanation = llm_result.get("explanation", "No explanation provided.")
    llm_sentiment = llm_result.get("news_sentiment", {})

    return {
        "ticker": ticker.upper(),
        "as_of": str(date.today()),
        "momentum": momentum_data,
        "news": news_data,
        "pulse": pulse,
        "llm_explanation": explanation,
        "news_sentiment": {
            "avg_score": avg_score,
            "label": sentiment_label,
            "summary": sentiment_summary,
        },
        "llm_sentiment_meta": llm_sentiment,
    }
