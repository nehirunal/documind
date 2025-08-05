import requests
import feedparser

def get_latest_headlines(rss_url, limit=5):
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(rss_url, headers=headers)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    entries = feed.entries[:limit]
    headlines = [f"{e.title}: {e.link}" for e in entries]

    joined = "\n".join(headlines)
    if len(joined) > 2000:
        joined = joined[:2000] + "\n...\n(devamı kesildi)"
    return joined if headlines else "Hiç haber bulunamadı."




if __name__ == "__main__":
    print(get_latest_headlines("https://www.ntv.com.tr/rss"))
