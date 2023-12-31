import json
import os
import datetime
import sys
import csv
import time
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from whoosh.index import create_in, open_dir, Index
from whoosh.writing import IndexWriter
from whoosh.fields import TEXT, DATETIME, ID, Schema


load_dotenv()
BLOG_FEED = os.getenv("BLOG_FEED")
BLOG_PATH_PREFIX = os.getenv("BLOG_PATH_PREFIX")


def initialize():
    schema = Schema(
        path=ID(unique=True, stored=True),
        title=TEXT(stored=True),
        subtitle=TEXT(stored=True),
        date=TEXT(stored=True),
        image_url=TEXT(stored=True),
        content=TEXT,
    )
    return create_in("data", schema)


def import_local(index: Index):
    if not os.path.exists("data/posts.csv"):
        return

    items = {}

    try:
        writer: IndexWriter = index.writer()

        with open("data/posts.csv") as fp:
            for i,row in enumerate(csv.reader(fp)):
                if i == 0:
                    continue

                fname, date, *_, title, subtitle, _ = row

                if not title:
                    continue

                with open("data/posts/%s.html" % fname) as fp:
                    soup = BeautifulSoup(fp.read(), "html")
                    content = soup.get_text("\n")
                    img = soup.find('img')

                data = dict(
                    path=BLOG_PATH_PREFIX + fname.split(".")[1],
                    title=title,
                    subtitle=subtitle,
                    date=date.split(".")[0],
                    image_url=img.attrs['src'] if img is not None else "",
                )
                print(data)
                items[data['path']] = dict(**data)

                data["content"] = str(content)
                writer.update_document(**data)

        return items

    finally:
        writer.commit()



def download(index: Index, items):
    print(f"Downloading {BLOG_FEED}")
    soup = BeautifulSoup(requests.get(BLOG_FEED).content, "xml")
    print("Feed downloaded, indexing...")

    try:
        writer: IndexWriter = index.writer()

        for item in soup.channel.find_all("item"):
            content = BeautifulSoup(
                item.find("content:encoded").get_text("\n"), "html"
            ).get_text()
            data = dict(
                path=str(item.link.string),
                title=str(item.title.string),
                subtitle=str(item.description.string),
                # Thu, 16 Nov 2023 00:34:08 GMT
                #  %a, %d %b  %Y   %H:%M:%S GMT
                date=datetime.datetime.strptime(str(item.pubDate.string), r"%a, %d %b %Y %H:%M:%S GMT").strftime("%Y-%m-%dT%H:%M:%S"),
                image_url=item.enclosure.attrs['url']
            )
            print(data)
            items[data['path']] = dict(**data)

            data["content"] = str(content)
            writer.update_document(**data)

    finally:
        writer.commit()


if __name__ == "__main__":
    index = initialize()

    items = import_local(index)

    while True:
        download(index, items)

        with open("data/items.json", "w") as fp:
            json.dump(items, fp, indent=4)

        if len(sys.argv) > 1:
            time.sleep(int(sys.argv[1]))
        else:
            break
