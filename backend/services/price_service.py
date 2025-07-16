import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# ✅ Load keys
ALPHA_KEY = os.getenv("ALPHAVANTAGE_KEY")
TWELVE_KEY = os.getenv("TWELVEDATA_KEY", "demo")  # optional fallback

if not ALPHA_KEY:
    raise ValueError("❌ ALPHAVANTAGE_KEY not found in .env file!")

async def fetch_alpha_vantage(ticker: str):
    """Fetch last 6 days from Alpha Vantage"""
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={ALPHA_KEY}"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        data = resp.json()

    if "Time Series (Daily)" not in data:
        print(f"❌ Alpha Vantage Error for {ticker}: {data}")
        return None  # signal failure
    return data["Time Series (Daily)"]

async def fetch_twelve_data(ticker: str):
    """Fallback: Fetch last 6 days from Twelve Data"""
    url = f"https://api.twelvedata.com/time_series?symbol={ticker}&interval=1day&outputsize=6&apikey={TWELVE_KEY}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        data = resp.json()

    if "values" not in data:
        print(f"❌ Twelve Data Error for {ticker}: {data}")
        return None

    # Convert to Alpha Vantage-like dict
    converted = {}
    for item in data["values"]:
        date = item["datetime"]
        converted[date] = {
            "4. close": item["close"]
        }
    return converted

async def get_price_momentum(ticker: str):
    """
    Fetch last 5 daily returns.
    First tries Alpha Vantage → falls back to Twelve Data if needed.
    """
    time_series = await fetch_alpha_vantage(ticker)

    # ✅ If Alpha Vantage fails, fallback to Twelve Data
    if not time_series:
        time_series = await fetch_twelve_data(ticker)

    # If both fail → return safe default
    if not time_series:
        return {"returns": [], "score": 0}

    # ✅ Get last 6 closing prices
    dates = sorted(time_series.keys(), reverse=True)[:6]
    closes = [float(time_series[d]["4. close"]) for d in dates]

    # ✅ Calculate daily returns %
    returns = []
    for i in range(len(closes) - 1):
        r = ((closes[i] - closes[i + 1]) / closes[i + 1]) * 100
        returns.append(round(r, 2))

    last5_returns = returns[:5]

    # ✅ Momentum score = avg return
    score = round(sum(last5_returns) / len(last5_returns), 2) if last5_returns else 0

    return {
        "returns": last5_returns,
        "score": score
    }
