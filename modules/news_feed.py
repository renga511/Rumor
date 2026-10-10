"""
News Feed Module - Fetches live news from multiple regions
"""
import feedparser

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def _parse_feed(url, max_items=10):
    try:
        feed = feedparser.parse(url, agent=UA)
        results = []
        for e in feed.entries[:max_items]:
            source = ""
            if hasattr(e, 'source') and hasattr(e.source, 'title'):
                source = e.source.title
            elif ' - ' in getattr(e, 'title', ''):
                source = e.title.split(' - ')[-1].strip()
            else:
                source = "News"
            results.append({
                "title": getattr(e, 'title', 'No title').split(' - ')[0].strip(),
                "link": getattr(e, 'link', '#'),
                "source": source,
                "published": getattr(e, 'published', '')
            })
        return results
    except Exception:
        return []

def get_india_news(max_total=12):
    urls = [
        "https://news.google.com/rss/search?q=India+breaking+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRHdvSkwyMHZNR2RqTWdvQVABUAFqAggAKAA?hl=en-IN&gl=IN&ceid=IN:en",
    ]
    results = []
    for url in urls:
        results.extend(_parse_feed(url, max_total))
    # deduplicate
    seen = set()
    unique = []
    for r in results:
        if r['title'] not in seen:
            seen.add(r['title'])
            unique.append(r)
    return unique[:max_total]

def get_world_news(max_total=12):
    urls = [
        "https://news.google.com/rss/search?q=world+news+breaking&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
    ]
    results = []
    for url in urls:
        results.extend(_parse_feed(url, max_total))
    seen = set()
    unique = []
    for r in results:
        if r['title'] not in seen:
            seen.add(r['title'])
            unique.append(r)
    return unique[:max_total]
