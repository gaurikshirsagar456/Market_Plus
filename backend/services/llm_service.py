import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
from textblob import TextBlob
from cachetools import TTLCache

# ✅ Load environment variables
load_dotenv()

# ✅ Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file!")

genai.configure(api_key=GEMINI_API_KEY)

# ✅ Use a valid Gemini model
model = genai.GenerativeModel("models/gemini-1.5-flash")

# ✅ Cache Gemini responses for 10 minutes
gemini_cache = TTLCache(maxsize=100, ttl=600)  # 100 tickers, 600s (10min)


def summarize_news_sentiment(news_data: list):
    """
    Analyze news headlines sentiment using TextBlob.
    Returns:
      - avg_sentiment (-1 to +1)
      - sentiment_label (positive/negative/neutral)
      - short summary text
    """
    if not news_data:
        return 0.0, "neutral", "No recent news headlines."

    sentiments = []
    for n in news_data:
        text = f"{n['title']} {n['description'] or ''}"
        score = TextBlob(text).sentiment.polarity  # -1 (neg) to +1 (pos)
        sentiments.append(score)

    avg_score = sum(sentiments) / len(sentiments)

    # Classify sentiment
    if avg_score > 0.1:
        label = "positive"
    elif avg_score < -0.1:
        label = "negative"
    else:
        label = "neutral"

    summary_text = f"Average news sentiment: {avg_score:.2f} ({label})"
    return avg_score, label, summary_text


async def analyze_pulse(ticker: str, momentum_data: dict, news_data: list):
    """
    Call Gemini to analyze momentum & news, return pulse + explanation + sentiment meta
    """

    # ✅ Cache check first
    if ticker.upper() in gemini_cache:
        print(f"✅ Cache hit for {ticker.upper()}")
        return gemini_cache[ticker.upper()]

    # ✅ Compute news sentiment before sending to Gemini
    avg_sentiment, sentiment_label, sentiment_summary = summarize_news_sentiment(news_data)

    # ✅ Prepare stock data text
    momentum_text = f"Last 5-day returns: {momentum_data['returns']}, momentum score: {momentum_data['score']}"
    if news_data:
        headlines_text = "\n".join([f"- {n['title']}: {n['description']}" for n in news_data])
    else:
        headlines_text = "No major recent news."

    # ✅ Prompt for Gemini (with summarized sentiment)
    prompt = f"""
You are a financial analyst AI. Analyze the following stock data for {ticker}.

Momentum:
{momentum_text}

News Sentiment:
{sentiment_summary}

Latest News Headlines:
{headlines_text}

Based on the momentum score AND the summarized news sentiment, decide if the outlook for {ticker} for **tomorrow** is:
- bullish (positive),
- bearish (negative), or 
- neutral.

Then, explain briefly in 2-3 sentences why (reference BOTH momentum & news context).

✅ IMPORTANT: Respond **ONLY** in this strict JSON format (no extra text!):
{{
  "pulse": "bullish|bearish|neutral",
  "explanation": "Your reasoning here"
}}
"""

    try:
        # ✅ Call Gemini API
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        print("\n=== Gemini Raw Response ===")
        print(raw_text)
        print("===========================\n")

        # ✅ Try direct JSON parsing
        try:
            parsed = json.loads(raw_text)
            pulse = parsed.get("pulse", "neutral")
            explanation = parsed.get("explanation", "No explanation provided.")
        except:
            # ✅ Extract JSON only
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                pulse = parsed.get("pulse", "neutral")
                explanation = parsed.get("explanation", "No explanation provided.")
            else:
                pulse, explanation = "neutral", "Gemini response unclear. Defaulting to neutral."

        # ✅ Build final structured response
        final_response = {
            "pulse": pulse,
            "explanation": explanation,
            "news_sentiment": {
                "score": avg_sentiment,
                "label": sentiment_label,
                "summary": sentiment_summary
            }
        }

        # ✅ Cache the result for 10 min
        gemini_cache[ticker.upper()] = final_response
        return final_response

    except Exception as e:
        print("❌ Gemini API error:", e)
        return {
            "pulse": "neutral",
            "explanation": "Momentum is unclear due to an API error.",
            "news_sentiment": {
                "score": 0.0,
                "label": "neutral",
                "summary": "API error prevented sentiment analysis."
            }
        }
