import os
import re
import json
import time
import codecs
import logging
import subprocess

from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from html.parser import HTMLParser

from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS


app = Flask(__name__)

CORS(
    app,
    origins=[
        "http://0.0.0.0:8003",
        "http://147.224.251.137:8003",
    ],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==========================================================
# CONFIGURATION
# ==========================================================

DEFAULT_COMPANY_CODE = "TATAGOLD"

DEFAULT_INTERVAL = 60
MIN_INTERVAL = 5
CHUNK_SIZE = 16 * 1024


# ==========================================================
# COMPANY CODE / URL
# ==========================================================

def get_screener_url(company_code):
    """
    Convert a company code such as TATAGOLD into its
    Screener.in consolidated company URL.
    """

    if not company_code:
        raise ValueError("Company code is required")

    company_code = company_code.strip().upper()

    if not re.fullmatch(r"[A-Z0-9_-]+", company_code):
        raise ValueError("Invalid company code")

    return (
        f"https://www.screener.in/company/"
        f"{company_code}/consolidated/"
    )


# ==========================================================
# HTML PARSER
# ==========================================================

class ScreenerParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.in_ratios = False
        self.in_h1 = False

        self.current_li = None
        self.current_span = None

        self.company_parts = []
        self.ratios = {}

    def handle_starttag(self, tag, attrs):

        attrs = dict(attrs)

        if tag == "h1":
            self.in_h1 = True

        if tag == "ul" and attrs.get("id") == "top-ratios":
            self.in_ratios = True

        if self.in_ratios and tag == "li":
            self.current_li = {
                "name": "",
                "numbers": []
            }

        if self.current_li and tag == "span":

            classes = attrs.get("class", "").split()

            if "name" in classes:
                self.current_span = "name"

            elif "number" in classes:
                self.current_span = "number"

    def handle_data(self, data):

        if self.in_h1:
            self.company_parts.append(data)

        if self.current_li and self.current_span:

            if self.current_span == "name":
                self.current_li["name"] += data

            elif self.current_span == "number":
                self.current_li["numbers"].append(data)

    def handle_endtag(self, tag):

        if tag == "h1":
            self.in_h1 = False

        if tag == "span":
            self.current_span = None

        if tag == "li" and self.current_li:

            name = " ".join(
                self.current_li["name"].split()
            )

            numbers = [
                to_number(value)
                for value in self.current_li["numbers"]
            ]

            if name:
                self.ratios[name] = (
                    numbers if len(numbers) > 1
                    else numbers[0] if numbers
                    else None
                )

            self.current_li = None

        if tag == "ul" and self.in_ratios:
            self.in_ratios = False

    def get_result(self):

        company = " ".join(
            "".join(self.company_parts).split()
        )

        return {
            "company": company or None,
            "ratios": self.ratios
        }


# ==========================================================
# NUMBER CONVERSION
# ==========================================================

def to_number(value):

    if value is None:
        return None

    value = str(value).replace(",", "").strip()

    match = re.search(
        r"[-+]?\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    try:
        number = float(match.group())

        if number.is_integer():
            return int(number)

        return number

    except (ValueError, OverflowError):
        return None


# ==========================================================
# URL VALIDATION
# ==========================================================

def validate_url(url):

    parsed = urlsplit(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname not in {
            "screener.in",
            "www.screener.in"
        }
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            "Only HTTPS Screener.in company URLs are allowed"
        )

    if not parsed.path.startswith("/company/"):
        raise ValueError(
            "Invalid Screener.in company URL"
        )

    return url


# ==========================================================
# STREAM HTTP RESPONSE
# ==========================================================

def fetch_page(url):

    validate_url(url)

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (portfolio-stream/1.0)",
            "Accept": "text/html",
        }
    )

    parser = ScreenerParser()

    chunks = 0
    total_chars = 0

    decoder = codecs.getincrementaldecoder("utf-8")(
        errors="replace"
    )

    with urlopen(req, timeout=30) as response:

        if response.status != 200:
            raise Exception(
                f"HTTP {response.status}"
            )

        while True:

            chunk = response.read(CHUNK_SIZE)

            if not chunk:
                break

            text = decoder.decode(
                chunk,
                final=False
            )

            parser.feed(text)

            chunks += 1
            total_chars += len(text)

        remaining = decoder.decode(
            b"",
            final=True
        )

        if remaining:
            parser.feed(remaining)
            total_chars += len(remaining)

        parser.close()

    result = parser.get_result()

    return {
        **result,
        "chunks": chunks,
        "totalChars": total_chars
    }


# ==========================================================
# SNAPSHOT GENERATOR
# ==========================================================

def to_snapshot(url):

    result = fetch_page(url)

    ratios = result["ratios"]

    high_low = ratios.get("High / Low")

    if isinstance(high_low, list):
        high = high_low[0] if len(high_low) > 0 else None
        low = high_low[1] if len(high_low) > 1 else None
    else:
        high = None
        low = None

    return {
        "time": datetime.now(
            timezone.utc
        ).isoformat(),

        "company": result["company"],

        "price": ratios.get("Current Price"),

        "marketCap": ratios.get("Market Cap"),

        "stockPE": ratios.get("Stock P/E"),

        "high": high,

        "low": low,

        "ratios": ratios,

        "chunks": result["chunks"],

        "totalChars": result["totalChars"]
    }


# ==========================================================
# ONE-TIME SCREENER API
# ==========================================================

@app.route(
    "/api/screener/snapshot",
    methods=["GET"]
)
def screener_snapshot():

    try:

        company_code = request.args.get(
            "company",
            DEFAULT_COMPANY_CODE
        )

        company_code = company_code.strip().upper()
        url = get_screener_url(company_code)

        snapshot = to_snapshot(url)

        if snapshot["price"] is None:

            return jsonify({
                "success": False,
                "companyCode": company_code,
                "message": (
                    "No price found. "
                    "The page layout may have changed "
                    "or the request was blocked."
                ),
                "data": snapshot
            }), 422

        return jsonify({
            "success": True,
            "companyCode": company_code,
            "data": snapshot
        })

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:

        logger.exception("Screener snapshot failed")

        return jsonify({
            "success": False,
            "message": str(error)
        }), 502


# ==========================================================
# CONTINUOUS PRICE STREAM
# ==========================================================

def price_stream(url, every_sec):

    last_key = None

    while True:

        try:

            snapshot = to_snapshot(url)

            key = json.dumps(
                [
                    snapshot["price"],
                    snapshot["marketCap"],
                    snapshot["stockPE"]
                ],
                sort_keys=True
            )

            changed = key != last_key

            record = {
                **snapshot,
                "changed": changed
            }

            last_key = key

        except Exception as error:

            logger.exception(
                "Screener polling failed"
            )

            record = {
                "time": datetime.now(
                    timezone.utc
                ).isoformat(),
                "error": str(error)
            }

        yield json.dumps(record) + "\n"

        time.sleep(every_sec)


@app.route(
    "/api/screener/stream",
    methods=["GET"]
)
def screener_stream():

    try:

        company_code = request.args.get(
            "company",
            DEFAULT_COMPANY_CODE
        )

        company_code = company_code.strip().upper()
        url = get_screener_url(company_code)

        every_sec = max(
            MIN_INTERVAL,
            int(request.args.get(
                "every",
                DEFAULT_INTERVAL
            ))
        )

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    return Response(

        stream_with_context(
            price_stream(url, every_sec)
        ),

        mimetype="application/x-ndjson",

        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ==========================================================
# EXISTING PORTFOLIO SIGNALS API
# ==========================================================

@app.route(
    "/api/portfolio/signals",
    methods=["GET"]
)
def portfolio_signals():

    try:

        result = subprocess.run(
            ["bash", "runner.sh"],

            capture_output=True,

            text=True,

            timeout=120,

            env=os.environ.copy()
        )

        return jsonify({

            "success": result.returncode == 0,

            "exitCode": result.returncode,

            "output": result.stdout.strip(),

            "error": result.stderr.strip()

        }), (
            200 if result.returncode == 0 else 500
        )

    except subprocess.TimeoutExpired:

        return jsonify({
            "success": False,
            "message": "Script execution timed out"
        }), 504

    except Exception:

        logger.exception(
            "Portfolio signals execution failed"
        )

        return jsonify({
            "success": False,
            "message": "Failed to execute portfolio signals"
        }), 500


# ==========================================================
# SERVER
# ==========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=False,
        threaded=True
    )