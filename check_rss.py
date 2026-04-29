import requests
from bs4 import BeautifulSoup
import concurrent.futures

urls = [
    "https://www.tuscanitas.com",
    "https://www.beauxvillages.com",
    "https://www.romantichouses.com",
    "https://www.marchecountryhomes.com",
    "https://www.caseinlanga.it",
    "https://www.agenziailcasale.it",
    "https://www.aldeasabandonadas.com",
    "https://www.buscomasia.com",
    "https://www.lancoisdoval.es",
    "https://www.gaiainmobiliariarural.com",
    "https://www.rusticaestates.com",
    "https://www.rusur.es",
    "https://www.portugalrur.pt",
    "https://www.entreportas.pt"
]

def check_rss(url):
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('link', type=['application/rss+xml', 'application/atom+xml'])
        rss_urls = [link.get('href') for link in links]
        if not rss_urls:
            # Also look for common paths
            for path in ['/feed', '/rss', '/rss.xml']:
                try:
                    feed_resp = requests.head(url.rstrip('/') + path, timeout=5)
                    if feed_resp.status_code == 200 and 'xml' in feed_resp.headers.get('Content-Type', '').lower():
                        rss_urls.append(url.rstrip('/') + path)
                except:
                    pass
        return url, rss_urls
    except Exception as e:
        return url, str(e)

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(check_rss, urls))

for url, feeds in results:
    if isinstance(feeds, list):
        if feeds:
            print(f"✅ {url} -> Feeds found: {feeds}")
        else:
            print(f"❌ {url} -> No feeds found")
    else:
        print(f"⚠️ {url} -> Error: {feeds}")
