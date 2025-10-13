import requests
from pprint import pprint
from feedendum import Feed, FeedItem, to_rss_string
from urllib.parse import urljoin
from itertools import chain
from datetime import datetime as dt, timedelta
import tempfile
import os

NSITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
def url_to_filename(url: str) -> str:
    return url.split("/")[-1] + ".xml"

BASEURL = "https://www.raiplaysound.it/programmi/ilruggitodelconiglio"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Referer": "https://www.raiplaysound.it/"
}
def _datetime_parser(s: str) -> dt:
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            return dt.strptime(s, fmt)
        except ValueError:
            continue
    return dt.now()


def parseplaylist(BASEURL:str) -> dict:
    playlistjson = requests.get(BASEURL + ".json").json()

# pprint(playlistjson)

    return playlistjson


def requestFileURL(url):
    global HEADERS
    response = requests.get(url, headers = HEADERS, stream = True, allow_redirects=True)
    if response.url.endswith(".mp3"):
        return response.url
    else:
        contenuto_m3u8 = response.text
        m3u_parse = contenuto_m3u8.rsplit("\n")
        m3u_parse.pop(-1)
        return response.url.replace("playlist.m3u8", m3u_parse[-1])

playlistjson = parseplaylist(BASEURL)
episodes : list = playlistjson.get("block", {}).get("cards", [])

def extractEpisodeUrl(episode) -> str:
    url = episode.get("audio", {}).get("url", "")
    if url.startswith("ttp"):
        url = url.replace("ttp", "https")
    return url





class RaiParser:
    
    def __init__(self, url: str, folderPath: str) -> None:
        self.url = url
        self.folderPath = folderPath if folderPath else os.getcwd()

    def process(self) -> None:
        global VALUE
        response = requests.get(self.url + ".json")
        response.raise_for_status()
        rdata = response.json()

        feed = Feed()
        feed.title = rdata["title"]
        feed.description = rdata["podcast_info"].get("description", rdata["title"])
        feed.url = self.url
        feed._data["image"] = {"url": urljoin(self.url, rdata["podcast_info"]["image"])}
        feed._data[f"{NSITUNES}author"] = "RaiPlaySound"
        feed._data["language"] = "it-it"
        feed._data[f"{NSITUNES}owner"] = {f"{NSITUNES}email": "giuliomagnifico@gmail.com"}

        categories = {c["name"] for c in chain(
            rdata["podcast_info"]["genres"],
            rdata["podcast_info"]["subgenres"],
            rdata["podcast_info"]["dfp"].get("escaped_genres", []),
            rdata["podcast_info"]["dfp"].get("escaped_typology", []),
        )}

        feed._data[f"{NSITUNES}category"] = [{"@text": c} for c in sorted(categories)]

        cards = rdata["block"].get("cards", [])
        feed.items = []

        for item in cards:
            if not item.get("audio"):
                continue

            fitem = FeedItem()
            fitem.title = item["toptitle"]
            fitem.id = "giuliomagnifico-raiplay-feed-" + item["uniquename"]
            fitem.update = _datetime_parser(item["track_info"].get("date", dt.now().isoformat()))
            fitem.url = urljoin(self.url, item["track_info"]["page_url"])
            fitem.content = item.get("description", item["title"])

            enclosure_url = item["audio"].get("url")
            relinkURL = extractEpisodeUrl(item)

            fileUrl = requestFileURL(relinkURL)

            fitem._data = {
                "enclosure": {
                    "@type": "audio/mpeg",
                    "@url": fileUrl,
                },
                f"{NSITUNES}title": fitem.title,
                f"{NSITUNES}summary": fitem.content,
                f"{NSITUNES}duration": item["audio"]["duration"],
                "image": {"url": urljoin(self.url, item["image"])},
            }

            feed.items.append(fitem)

        feed.items.sort(key=lambda x: x.update, reverse=True)

        filename = os.path.join(self.folderPath, url_to_filename(self.url))
        atomic_write(filename, to_rss_string(feed))

def atomic_write(filename, content: str):
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf8", delete=False,
        dir=os.path.dirname(filename), prefix=".tmp-single-", suffix=".xml"
    )
    tmp.write(content)
    tmp.close()
    os.replace(tmp.name, filename)

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Genera RSS da RaiPlaySound",
        epilog="Info su https://github.com/giuliomagnifico/raiplay-feed/"
    )

    parser.add_argument("url", help="URL podcast RaiPlaySound")
    parser.add_argument("-f", "--folder", default=".", help="Cartella output")

    args = parser.parse_args()

    rai_parser = RaiParser(args.url, args.folder)
    rai_parser.process()

if __name__ == "__main__":
    main()




# percorso_relativo = contenuto_m3u8.split('\n')[3].strip() # es: chunklist_b1758000...m3u8
