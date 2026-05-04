from trading_signal_agent.news import parse_rss, relevant_news, summarize_news


def test_parse_rss_and_sentiment() -> None:
    xml = b"""
    <rss><channel>
      <item>
        <title>Bitcoin ETF approved after strong adoption</title>
        <link>https://example.com/btc</link>
        <pubDate>Mon, 04 May 2026 00:00:00 GMT</pubDate>
      </item>
    </channel></rss>
    """
    items = parse_rss(xml, "fixture")
    assert len(items) == 1
    assert items[0].sentiment > 0
    matched = relevant_news(items, "BTC")
    score, summary = summarize_news(matched)
    assert score > 0
    assert "bullish" in summary
