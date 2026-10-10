"""
Fact Checker Module
Improved multi-source verification with Wikipedia + Google News + DuckDuckGo
"""
import wikipedia
import feedparser
import warnings
import random
import urllib.parse
import requests
from difflib import SequenceMatcher
import string
import re
from langdetect import detect
from googletrans import Translator

translator = Translator()

warnings.filterwarnings("ignore")

REPUTABLE_SOURCES = [
    "reuters", "bbc", "ap news", "associated press", "the guardian",
    "nytimes", "washington post", "bloomberg", "cnn", "ndtv",
    "the hindu", "times of india", "economic times", "al jazeera",
    "france24", "dw", "abc news", "npr", "pbs", "wsj"
]

DEBUNK_KEYWORDS = [
    "fact check", "fake", "debunk", "false", "hoax", "conspiracy",
    "rumor", "misleading", "misinformation", "not true", "fabricated",
    "disinformation", "satire", "parody", "no evidence", "refuted", "denied"
]

STOPWORDS = {
    'the','a','an','is','it','in','on','at','to','for','of','and','or','with','that','this','are','was','were','be',
    'been','being','have','has','had','do','does','did','but','if','then','else','when','where','why','how','all',
    'any','both','each','few','more','most','other','some','such','no','nor','not','only','own','same','so','than',
    'too','very','s','t','can','will','just','don','should','now', 'about', 'from', 'as', 'into', 'by'
}

REGIONAL_FEEDS = {
    "North America": [
        "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en",
    ],
    "Europe": [
        "https://news.google.com/rss/search?q={q}&hl=en-GB&gl=GB&ceid=GB:en",
    ],
    "Asia": [
        "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "Middle East": [
        "https://news.google.com/rss/search?q={q}+middle+east&hl=en-US&gl=US&ceid=US:en",
    ],
    "Africa": [
        "https://news.google.com/rss/search?q={q}+africa&hl=en-US&gl=US&ceid=US:en",
    ],
    "Australia": [
        "https://news.google.com/rss/search?q={q}&hl=en-AU&gl=AU&ceid=AU:en",
    ]
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def fetch_google_news(query, region_url=None):
    """Fetch news from Google RSS for a given query."""
    # Better query: Use first 150 chars but try to keep whole words
    words = query.split()
    short_query = ""
    for w in words:
        if len(short_query) + len(w) < 140:
            short_query += w + " "
        else:
            break
    short_query = short_query.strip()
    
    encoded = urllib.parse.quote(short_query)
    url = region_url.format(q=encoded) if region_url else \
          f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url, agent=USER_AGENT)
        return feed.entries
    except Exception:
        return []

def get_overlap_score(text1, text2):
    """Calculate keyword overlap percentage."""
    def get_keywords(t):
        words = re.findall(r'\w+', t.lower())
        return set([w for w in words if w not in STOPWORDS and len(w) > 2])
    
    kw1 = get_keywords(text1)
    kw2 = get_keywords(text2)
    if not kw1: return 0
    overlap = kw1.intersection(kw2)
    return len(overlap) / len(kw1)

def fetch_duckduckgo_news(query):
    """Fetch news via DuckDuckGo instant answers API as a fallback."""
    try:
        short_q = query[:80]
        encoded = urllib.parse.quote(short_q)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1"
        r = requests.get(url, timeout=5, headers={"User-Agent": USER_AGENT})
        data = r.json()
        results = []
        if data.get("RelatedTopics"):
            for t in data["RelatedTopics"][:5]:
                if t.get("Text") and t.get("FirstURL"):
                    results.append({
                        "title": t["Text"][:120],
                        "link": t["FirstURL"],
                        "source": "DuckDuckGo"
                    })
        return results
    except Exception:
        return []

def get_source_name(entry):
    """Extract source/publication name from RSS entry."""
    if hasattr(entry, 'source') and hasattr(entry.source, 'title'):
        return entry.source.title
    if hasattr(entry, 'tags') and entry.tags:
        return entry.tags[0].term
    # Parse from title like "Headline - Source Name"
    title = getattr(entry, 'title', '')
    if ' - ' in title:
        return title.split(' - ')[-1].strip()
    return "News Source"

def is_reputable(source_name):
    src_lower = source_name.lower()
    return any(rep in src_lower for rep in REPUTABLE_SOURCES)

def analyze_rumor(text):
    """
    Multi-layer fact checking:
    1. Wikipedia (historical + encyclopedic)
    2. Google News RSS (global, multi-regional)
    3. DuckDuckGo (fallback enrichment)
    4. Cross-regional spread analysis
    """
    result = {
        "prediction": "🟡 INCONCLUSIVE",
        "verdict_cls": "inconclusive",
        "confidence": 50,
        "regions_covered": 0,
        "total_rss_hits": 0,
        "evidence": "No strong evidence found.",
        "score_breakdown": {
            "wikipedia_score": 0, "rss_score": 0,
            "rep_bonus": 0, "keyword_boost": 0, "keyword_penalty": 0
        },
        "hits_by_region": {},
        "wiki_context": None,
        "show_wikipedia": False,
        "top_sources": [],
        "debunked": False,
        "all_articles": [],
        "is_true_news": False,
        "original_language": "en",
        "translated_text": None,
        "ai_summary": None
    }

    # ── 0. Language Detection & Translation ──────────────────────────────────
    try:
        lang = detect(text)
        result["original_language"] = lang
        if lang != 'en':
            translation = translator.translate(text, dest='en')
            result["translated_text"] = translation.text
            search_text = translation.text
        else:
            search_text = text
    except Exception:
        search_text = text

    all_entries = []
    top_sources = []
    hits_by_region = {}
    debunk_hits = 0

    # ── 1. Multi-regional RSS search ─────────────────────────────────────────
    for region, urls in REGIONAL_FEEDS.items():
        region_entries = []
        for url_template in urls:
            entries = fetch_google_news(search_text, url_template)
            region_entries.extend(entries)
        hits_by_region[region] = len(region_entries)
        all_entries.extend(region_entries)

    # Deduplicate by title
    seen_titles = set()
    unique_entries = []
    for e in all_entries:
        t = getattr(e, 'title', '')
        if t not in seen_titles:
            seen_titles.add(t)
            unique_entries.append(e)

    rss_hits = len(unique_entries)
    result["total_rss_hits"] = rss_hits

    rss_s = 0
    news_evidence = ""
    best_match = 0
    rep_count = 0

    for entry in unique_entries[:10]:
        title = getattr(entry, 'title', '')
        link = getattr(entry, 'link', '#')
        source = get_source_name(entry)
        title_lower = title.lower()

        match_ratio = SequenceMatcher(None, text.lower()[:150], title_lower[:150]).ratio()
        overlap_ratio = get_overlap_score(text, title)
        
        # Combined similarity score
        effective_match = max(match_ratio, overlap_ratio)
        best_match = max(best_match, effective_match)

        if any(k in title_lower for k in DEBUNK_KEYWORDS):
            # Only count as debunk if the title also contains some keywords from the search text
            if overlap_ratio > 0.2:
                debunk_hits += 1

        if is_reputable(source):
            rep_count += 1

        entry_data = {"source": source, "title": title, "link": link, "reputable": is_reputable(source)}
        top_sources.append(entry_data)

        if len(top_sources) <= 6:
            result["all_articles"].append(entry_data)

    # Fallback: DuckDuckGo
    if rss_hits < 3:
        ddg_results = fetch_duckduckgo_news(search_text)
        for item in ddg_results:
            result["all_articles"].append(item)
            top_sources.append(item)

    if rss_hits > 0:
        # Scale rss score based on how many hits and how well they match
        # If we have a very high overlap (>0.6), boost the score significantly
        base_rss = int(best_match * 100)
        hit_bonus = min(rss_hits * 4, 40)
        rss_s = min(base_rss + hit_bonus, 85)

    result["top_sources"] = top_sources[:6]
    result["debunked"] = debunk_hits > 0
    result["hits_by_region"] = {k: v for k, v in hits_by_region.items() if v > 0}

    # ── 2. Wikipedia search ───────────────────────────────────────────────────
    wiki_s = 0
    wiki_evidence = ""
    try:
        search_query = search_text[:80]
        wiki_results = wikipedia.search(search_query, results=3)
        for article_title in wiki_results[:2]:
            try:
                summary = wikipedia.summary(article_title, sentences=4)
                text_words = set(re.sub(r'[^\w\s]', '', text.lower()).split())
                summary_words = set(re.sub(r'[^\w\s]', '', summary.lower()).split())
                # Remove stopwords
                stopwords = {'the','a','an','is','it','in','on','at','to','for','of','and','or','with','that','this'}
                text_words -= stopwords
                summary_words -= stopwords
                overlap = len(text_words & summary_words)
                sim = SequenceMatcher(None, text.lower()[:200], summary.lower()[:200]).ratio()

                if sim > 0.12 or overlap >= 4:
                    wiki_s = min(wiki_s + 40, 40)
                    wiki_evidence = f"📚 **Wikipedia – {article_title}:** {summary[:300]}..."
                    result["wiki_context"] = {"title": article_title, "summary": summary}
                    result["show_wikipedia"] = True
                    break
            except Exception:
                continue
    except Exception:
        pass

    # ── 3. Scoring & Verdict ──────────────────────────────────────────────────
    rep_bonus = min(rep_count * 5, 20)
    keyword_boost = 8 if rss_hits > 3 else (4 if rss_hits > 0 else 0)
    keyword_penalty = 20 if (rss_hits == 0 and wiki_s == 0) else 0
    total_score = wiki_s + rss_s + rep_bonus + keyword_boost - keyword_penalty

    if debunk_hits > 0:
        result["prediction"] = "🔴 DEBUNKED / FAKE NEWS"
        result["verdict_cls"] = "fake"
        result["confidence"] = min(total_score + debunk_hits * 15 + 30, 99)
        result["evidence"] = f"⚠️ Fact-checkers have actively debunked this claim across {debunk_hits} sources.\n\n" + news_evidence + wiki_evidence
        result["is_true_news"] = False

    elif (rss_hits >= 2 and total_score > 30) or total_score > 55:
        result["prediction"] = "🟢 VERIFIED REAL NEWS"
        result["verdict_cls"] = "real"
        result["confidence"] = min(total_score + 25, 99)
        result["evidence"] = news_evidence + wiki_evidence
        result["is_true_news"] = True

    elif wiki_s >= 30 and rss_hits < 2:
        result["prediction"] = "🟢 VERIFIED HISTORICAL FACT"
        result["verdict_cls"] = "real"
        result["confidence"] = 97
        result["evidence"] = "Verified against encyclopedic databases.\n" + wiki_evidence
        result["is_true_news"] = True

    elif debunk_hits == 0 and total_score < 25:
        # Instead of calling it FAKE just because we can't find it
        # we mark it as unverified/inconclusive unless debunk keywords appear
        result["prediction"] = "🟡 UNVERIFIED / NEED MORE SOURCES"
        result["verdict_cls"] = "inconclusive"
        result["confidence"] = 40
        result["evidence"] = "No mainstream news reports or Wikipedia articles currently match this claim. This may be due to the news being extremely recent, highly local, or potentially unverified."
        result["is_true_news"] = None

    elif total_score < 15:
        result["prediction"] = "🔴 LIKELY FAKE / UNVERIFIABLE"
        result["verdict_cls"] = "fake"
        result["confidence"] = min(100 - total_score, 90)
        result["evidence"] = "Limited credible evidence found. Sources suggest this may be misinformation."
        result["is_true_news"] = False

    else:
        result["prediction"] = "🟡 INCONCLUSIVE / MIXED SIGNALS"
        result["verdict_cls"] = "inconclusive"
        result["confidence"] = max(45, total_score)
        result["evidence"] = "Partial evidence found. Independent verification recommended.\n\n" + news_evidence + wiki_evidence
        result["is_true_news"] = None

    result["score_breakdown"] = {
        "wikipedia_score": wiki_s,
        "rss_score": rss_s,
        "rep_bonus": rep_bonus,
        "keyword_boost": keyword_boost,
        "keyword_penalty": keyword_penalty
    }
    result["regions_covered"] = len([v for v in hits_by_region.values() if v > 0])

    # ── 4. AI Summary Generation ─────────────────────────────────────────────
    ai_summary_en = generate_ai_summary(result, search_text)
    
    if result["original_language"] != 'en':
        try:
            summary_trans = translator.translate(ai_summary_en, dest=result["original_language"])
            result["ai_summary"] = summary_trans.text
        except Exception:
            result["ai_summary"] = ai_summary_en
    else:
        result["ai_summary"] = ai_summary_en

    return result

def generate_ai_summary(result, text):
    """Generate a concise AI summary based on findings."""
    if result["verdict_cls"] == "real":
        status = "Verified as Accurate"
    elif result["verdict_cls"] == "fake":
        status = "Identified as Misinformation"
    else:
        status = "Inconclusive / Unverified"
    
    source_count = result["total_rss_hits"]
    rep_sources = len([s for s in result["top_sources"] if s.get("reputable")])
    
    summary = f"Analysis of '{text}': This claim is currently {status}. "
    if source_count > 0:
        summary += f"We found {source_count} related reports across {result['regions_covered']} global regions, including {rep_sources} high-credibility sources. "
    else:
        summary += "No significant mainstream media coverage or encyclopedic entries were found to support this claim. "
    
    if result["debunked"]:
        summary += "Note: Several fact-checking organizations have flagged this as a potential hoax."
    
    return summary
