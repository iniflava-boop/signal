from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.request import urlopen

from .models import NewsItem


BULLISH_WORDS = {
    "adoption",
    "approve",
    "approved",
    "bullish",
    "breakthrough",
    "etf",
    "launch",
    "partnership",
    "rally",
    "surge",
    "upgrade",
}
BEARISH_WORDS = {
    "ban",
    "bearish",
    "collapse",
    "crackdown",
    "delay",
    "exploit",
    "hack",
    "lawsuit",
    "outage",
    "probe",
    "reject",
    "selloff",
}


class RssNewsClient:
    def __init__(self, feeds: list[str], timeout: int = 15) -> None:
        self.feeds = feeds
        self.timeout = timeout

    def fetch_recent(self, max_age_hours: int = 24) -> list[NewsItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        items: list[NewsItem] = []
        seen: set[str] = set()
        for feed in self.feeds:
            try:
                with urlopen(feed, timeout=self.timeout) as response:
                    content = response.read()
                for item in parse_rss(content, feed):
                    key = item.url or item.title.lower()
                    if key in seen or item.published_at < cutoff:
                        continue
                    seen.add(key)
                    items.append(item)
            except Exception:
                continue
        return sorted(items, key=lambda item: item.published_at, reverse=True)


def parse_rss(content: bytes, source: str) -> list[NewsItem]:
    root = ET.fromstring(content)
    raw_items = root.findall(".//item")
    if not raw_items:
        raw_items = root.findall("{http://www.w3.org/2005/Atom}entry")
    result: list[NewsItem] = []
    for raw in raw_items:
        title = _text(raw, "title")
        link = _text(raw, "link")
        if not link:
            atom_link = raw.find("{http://www.w3.org/2005/Atom}link")
            link = atom_link.attrib.get("href", "") if atom_link is not None else ""
        published = _text(raw, "pubDate") or _text(raw, "published") or _text(raw, "updated")
        if not title:
            continue
        result.append(
            NewsItem(
                title=clean_text(title),
                url=link,
                published_at=parse_date(published),
                source=source,
                sentiment=score_sentiment(title),
            )
        )
    return result


def relevant_news(items: list[NewsItem], base_asset: str, coin_name: str = "") -> list[NewsItem]:
    terms = {base_asset.lower()}
    if coin_name:
        terms.add(coin_name.lower())
    if base_asset.upper() == "BTC":
        terms.add("bitcoin")
    if base_asset.upper() == "ETH":
        terms.add("ethereum")
    matched = []
    for item in items:
        title = item.title.lower()
        if any(re.search(rf"\b{re.escape(term)}\b", title) for term in terms):
            matched.append(item)
    return matched[:5]


def summarize_news(items: list[NewsItem]) -> tuple[int, str]:
    if not items:
        return 0, "No major relevant RSS news found."
    score = sum(item.sentiment for item in items)
    labels = ", ".join(item.title for item in items[:2])
    sentiment = "bullish" if score > 0 else "bearish" if score < 0 else "neutral"
    return score, f"RSS sentiment {sentiment}: {labels}"


def score_sentiment(text: str) -> int:
    words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    return len(words & BULLISH_WORDS) - len(words & BEARISH_WORDS)


def parse_date(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _text(node: ET.Element, tag: str) -> str:
    found = node.find(tag)
    if found is None:
        found = node.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
    return found.text.strip() if found is not None and found.text else ""
