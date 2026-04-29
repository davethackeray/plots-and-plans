import requests
import xml.etree.ElementTree as ET

feeds = {
    "Tuscanitas": "https://www.tuscanitas.com/it/?format=feed&type=rss",
    "Beaux Villages": "https://www.beauxvillages.com/en/?format=feed&type=rss",
    "Marche Country Homes": "https://marchecountryhomes.com/feed/",
    "Case in Langa": "https://www.caseinlanga.it/feed/",
    "Agenzia Il Casale": "https://www.agenziailcasale.it/feed/",
    "Aldeas Abandonadas": "https://www.aldeasabandonadas.com/index.php?format=feed&type=rss",
    "Lancois Doval": "https://www.lancoisdoval.es/rss.xml",
    "Rustica Estates": "https://rusticaestates.com/feed/"
}

def check_feed(name, url):
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}, verify=False)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall('.//item')
            if not items:
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            print(f"[{name}] {url} -> Found {len(items)} items")
            if items:
                # Print title of first item
                title = items[0].find('title')
                title_text = title.text if title is not None else "No title"
                link = items[0].find('link')
                link_text = link.text if link is not None else (link.get('href') if hasattr(link, 'get') else "No link")
                print(f"  Sample: {title_text} ({link_text})")
        else:
            print(f"[{name}] Failed with status {resp.status_code}")
    except Exception as e:
        print(f"[{name}] Error: {e}")

for name, url in feeds.items():
    check_feed(name, url)
