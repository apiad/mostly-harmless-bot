import os
import datetime
import sys
import time
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from whoosh.index import create_in, open_dir, Index
from whoosh.writing import IndexWriter
from whoosh.searching import Searcher
from whoosh.fields import TEXT, DATETIME, ID, Schema


load_dotenv()
BLOG_FEED = os.getenv("BLOG_FEED")


def initialize():
    if os.path.exists("data/.created"):
        return open_dir("data")

    schema = Schema(path=ID(unique=True, stored=True), title=TEXT(stored=True), subtitle=TEXT(stored=True), content=TEXT)
    index = create_in("data", schema)

    with open("data/.created", "w") as fp:
        fp.write(str(datetime.datetime.today()))

    return index


def download(index: Index):
    print(f"Downloading {BLOG_FEED}")
    soup = BeautifulSoup(requests.get(BLOG_FEED).content, "xml")
    print("Feed downloaded, indexing...")

    try:
        writer: IndexWriter = index.writer()

        for item in soup.channel.find_all("item"):
            content = BeautifulSoup(item.find("content:encoded").get_text(), "html").get_text()
            data = dict(path=item.link.string, title=item.title.string, subtitle=item.description.string)
            print(data)

            data['content'] = content
            writer.update_document(**{ k:str(v) for k,v in data.items() })

    finally:
        writer.commit()


if __name__ == "__main__":
    index = initialize()

    while True:
        download(index)

        if len(sys.argv) > 1:
            time.sleep(int(sys.argv[1]))
        else:
            break
