"""Current exchange directories for Taiwan and US stock/ETF scans."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import requests

URLS = {
    "twse": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2",
    "tpex": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4",
    "nasdaq": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "other": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}


class _Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag == "td":
            self.cell = []

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        if tag == "tr" and self.row:
            self.rows.append(self.row)


def taiwan_rows(text, exchange):
    table = _Table()
    table.feed(text)
    section = None
    rows = []
    for cells in table.rows:
        if len(cells) == 1:
            section = cells[0].strip()
            continue
        if len(cells) != 7 or section not in ("股票", "ETF"):
            continue
        parts = cells[0].split(maxsplit=1)
        if len(parts) != 2:
            continue
        code, name = parts
        if not re.fullmatch(r"\d{4,6}[A-Z]?", code):
            continue
        if cells[3] != ("上市" if exchange == "twse" else "上櫃"):
            continue
        rows.append(
            {
                "stock_id": code,
                "symbol": code + (".TW" if exchange == "twse" else ".TWO"),
                "name": name,
                "exchange": exchange,
                "kind": "stock" if section == "股票" else "etf",
                "market": "tw",
                "currency": "TWD",
                "timezone": "Asia/Taipei",
                "isin": cells[1],
                "listed_date": cells[2].replace("/", "-"),
                "industry_category": cells[4],
            }
        )
    if not rows:
        raise ValueError("Taiwan directory has no stock/ETF rows")
    return rows


def us_rows(text, source):
    rows = []
    excluded = []
    created = None
    for r in csv.DictReader(io.StringIO(text), delimiter="|"):
        code = r.get("Symbol") if source == "nasdaq" else r.get("ACT Symbol")
        if not code:
            continue
        if code.startswith("File Creation Time:"):
            created = code.partition(":")[2].strip()
            continue
        name = r.get("Security Name", "")
        reason = None
        if r.get("Test Issue") != "N":
            reason = "test_issue"
        elif r.get("ETF") == "N" and re.search(
            r"\b(warrants?|rights?|units?|preferred|preference|notes|debentures)\b", name, re.I
        ):
            reason = "non_common_stock_or_etf"
        elif r.get("ETF") == "Y" and re.search(r"\bETN\b|exchange.traded notes", name, re.I):
            reason = "exchange_traded_note"
        elif not re.fullmatch(r"[A-Z][A-Z0-9]*(?:\.[A-Z0-9]+)?", code):
            reason = "unsupported_security_notation"
        elif r.get("ETF") not in ("Y", "N"):
            reason = "unknown_instrument_type"
        if reason:
            excluded.append({"symbol": code, "name": name, "reason": reason})
            continue
        exchange = (
            "nasdaq"
            if source == "nasdaq"
            else {"N": "nyse", "A": "nyse-american", "P": "nyse-arca", "Z": "cboe", "V": "iex"}.get(
                r.get("Exchange"), "us-exchange-" + str(r.get("Exchange"))
            )
        )
        if exchange is None:
            excluded.append({"symbol": code, "name": name, "reason": "unmapped_exchange"})
            continue
        rows.append(
            {
                "stock_id": code,
                "symbol": code.replace(".", "-"),
                "name": name,
                "exchange": exchange,
                "kind": "etf" if r["ETF"] == "Y" else "stock",
                "market": "us",
                "currency": "USD",
                "timezone": "America/New_York",
                "directory_symbol": code,
            }
        )
    if not rows or not created:
        raise ValueError("US directory incomplete or missing timestamp")
    return rows, excluded, created


def fetch_directories():
    result = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "listings": [],
        "excluded": [],
    }
    for key, url in URLS.items():
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        text = response.content.decode("cp950" if key in ("twse", "tpex") else "utf-8")
        if key in ("twse", "tpex"):
            rows = taiwan_rows(text, key)
            created = None
        else:
            rows, excluded, created = us_rows(text, key)
            result["excluded"].extend(excluded)
        result["sources"][key] = {"url": url, "rows": len(rows), "file_creation_time": created}
        result["listings"].extend(rows)
    symbols = [row["symbol"] for row in result["listings"]]
    if len(symbols) != len(set(symbols)):
        raise ValueError("Duplicate directory symbol")
    return result
