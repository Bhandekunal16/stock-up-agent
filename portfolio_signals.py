import os
import sys
import random
from collections import defaultdict
from algorithm import algorithn_env, database_config
from pymongo import MongoClient

SHORT_MA = algorithn_env.SHORT_MA
LONG_MA = algorithn_env.LONG_MA
RSI_PERIOD = algorithn_env.RSI_PERIOD
MOMENTUM_DAYS = algorithn_env.MOMENTUM_DAYS
MOMENTUM_THRESHOLD = algorithn_env.MOMENTUM_THRESHOLD
RSI_OVERBOUGHT = algorithn_env.RSI_OVERBOUGHT
RSI_OVERSOLD = algorithn_env.RSI_OVERSOLD
CONCENTRATION_LIMIT = algorithn_env.CONCENTRATION_LIMIT
_client = None


def get_mongo_client():
    global _client
    if _client is None:
        uri = os.environ.get("MONGO_URI") or (
            sys.argv[1] if len(sys.argv) > 1 else None
        )
        if not uri:
            raise ValueError("MONGO_URI is not configured")
        _client = MongoClient(
            uri,
            maxPoolSize=database_config.maxPoolSize,
            minPoolSize=database_config.minPoolSize,
            maxIdleTimeMS=database_config.maxIdleTimeMS,
            serverSelectionTimeoutMS=database_config.serverSelectionTimeoutMS,
            connectTimeoutMS=database_config.connectTimeoutMS,
            retryReads=database_config.retryReads,
        )
    return _client


def load_documents(demo=False) -> list:
    if demo:
        return demo_documents()
    db = get_mongo_client()[database_config.db_name]
    collection = db[database_config.coll_name]
    cursor = collection.find({}).sort("date", 1).batch_size(1000)
    return list(cursor)


def build_series(docs):
    """Return {company: [(date, price_per_share), ...]} plus latest holdings."""
    series = defaultdict(list)
    latest = {}
    for doc in docs:
        date = doc["date"]
        for item in doc.get("data", []):
            shares = item.get("shares") or 0
            if shares <= 0:
                continue
            company = item["company"]
            price = item["currentValue"] / shares
            series[company].append((date, price))
            latest[company] = item
    return series, latest


def pct(new: int, old: int) -> float | int:
    if not old:
        return 0.0
    return ((new / old) - 1) * 100


def sma(values, n):
    length = len(values)
    if n <= 0 or length < n:
        return None
    return sum(values[length - n :]) / n


def rsi(values, period=RSI_PERIOD):
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for a, b in zip(values[-period - 1 : -1], values[-period:]):
        change = b - a
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def analyse(company, points, latest_item, total_value):
    prices = [p for _, p in points]
    last = prices[-1]

    day1 = pct(last, prices[-2]) if len(prices) >= 2 else None
    mom = pct(last, prices[-1 - MOMENTUM_DAYS]) if len(prices) > MOMENTUM_DAYS else None
    short = sma(prices, SHORT_MA)
    long_ = sma(prices, LONG_MA)
    r = rsi(prices)
    high = max(prices)
    drawdown = pct(last, high)
    weight = latest_item["currentValue"] / total_value * 100
    vs_ref = pct(latest_item["currentValue"], latest_item["referenceValue"])

    score = 0
    notes = []

    if short is not None and long_ is not None:
        if short > long_:
            score += 1
            notes.append("uptrend (MA%d > MA%d)" % (SHORT_MA, LONG_MA))
        else:
            score -= 1
            notes.append("downtrend (MA%d < MA%d)" % (SHORT_MA, LONG_MA))

    if mom is not None:
        if mom > MOMENTUM_THRESHOLD:
            score += 1
            notes.append("%dd momentum up" % MOMENTUM_DAYS)
        elif mom < -MOMENTUM_THRESHOLD:
            score -= 1
            notes.append("%dd momentum down" % MOMENTUM_DAYS)

    if r is not None:
        if r >= RSI_OVERBOUGHT:
            score -= 1
            notes.append("overbought (RSI %.0f)" % r)
        elif r <= RSI_OVERSOLD:
            score += 1
            notes.append("oversold (RSI %.0f)" % r)

    if weight >= CONCENTRATION_LIMIT:
        notes.append("CONCENTRATION %.0f%% of portfolio" % weight)

    if score >= 2:
        signal = "BUY-WATCH"
    elif score <= -2:
        signal = "SELL-WATCH"
    else:
        signal = "HOLD"

    return {
        "company": company,
        "days": len(prices),
        "price": last,
        "day1": day1,
        "mom": mom,
        "rsi": r,
        "drawdown": drawdown,
        "weight": weight,
        "vs_ref": vs_ref,
        "score": score,
        "signal": signal,
        "notes": "; ".join(notes),
    }


def fmt(x, spec="%.1f", suffix=""):
    return "n/a" if x is None else (spec % x) + suffix


def main():
    demo = "--demo" in sys.argv
    docs = load_documents(demo)
    if not docs:
        print("No documents found.")
        return

    series, latest = build_series(docs)
    total = sum(item["currentValue"] for item in latest.values())

    rows = [analyse(c, pts, latest[c], total) for c, pts in series.items()]
    rows.sort(key=lambda r: r["score"], reverse=True)

    print("Days of history: %d   Portfolio value: %.2f\n" % (len(docs), total))
    header = "%-22s %9s %7s %7s %6s %8s %7s %8s  %-11s" % (
        "Company",
        "Price",
        "1d%",
        "5d%",
        "RSI",
        "FromHigh",
        "Wt%",
        "vsRef%",
        "Signal",
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            "%-22s %9.2f %7s %7s %6s %8s %7.1f %8.1f  %-11s"
            % (
                r["company"],
                r["price"],
                fmt(r["day1"]),
                fmt(r["mom"]),
                fmt(r["rsi"], "%.0f"),
                fmt(r["drawdown"]),
                r["weight"],
                r["vs_ref"],
                r["signal"],
            )
        )
    print()
    for r in rows:
        if r["notes"]:
            print("%s: %s" % (r["company"], r["notes"]))

    print(
        "\nThese are heuristic signals from your own price history only. "
        "Not a prediction, not financial advice."
    )


def demo_documents():
    """Fake 17 days of data shaped like your documents, for testing."""
    random.seed(7)
    start = [
        ("Bank of Maharashtra", 16, 90.2, 45.69),
        ("Suzlon Energy", 11, 38.9, 34.56),
        ("METALIETF", 22, 12.8, 12.82),
        ("Canara Bank", 1, 132.3, 135.46),
        ("TATAGOLD", 30, 13.56, 14.46),
        ("Central Bank of India", 20, 32.04, 36.59),
        ("TATSILV", 10, 17.99, 23.55),
        ("Reliance Power", 50, 19.32, 27.04),
    ]
    prices = {c: p for c, _, p, _ in start}
    docs = []
    for day in range(17):
        data = []
        for c, shares, _, ref_price in start:
            prices[c] *= 1 + random.uniform(-0.03, 0.035)
            data.append(
                {
                    "company": c,
                    "shares": shares,
                    "currentValue": round(prices[c] * shares, 2),
                    "referenceValue": round(ref_price * shares, 2),
                }
            )
        docs.append(
            {"date": "2026-10-%02d" % (day + 12) if day < 20 else "", "data": data}
        )
    return docs


if __name__ == "__main__":
    main()
