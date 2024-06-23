#!/usr/bin/env python3
import os
from pathlib import Path
from threading import Thread
from bs4 import BeautifulSoup
from requests import get as fetch
from argparse import ArgumentParser
from urllib.parse import quote as url_quote
from urllib.parse import urljoin as url_join

SEARCH_URL = "https://ww8.mangakakalot.tv/search/"
MANGA_URL = "https://ww8.mangakakalot.tv/manga/"
CHAPTER_URL = "https://ww8.mangakakalot.tv/chapter/"

def args_get():
    parser = ArgumentParser(
        prog = "manga-dl",
        description = "Easily download manga from your terminal",
    )
    parser.add_argument('manga_name')
    parser.add_argument('-multi', action = 'store_true')
    parser.add_argument('-begin')
    parser.add_argument('-end')
    return parser.parse_args()

def manga_get_id_and_title(manga_name):
    if manga_name == "" or manga_name is None:
        print("error: please provide a valid manga name")
        return None
    # Send request
    url = url_join(SEARCH_URL, url_quote(manga_name))
    res = fetch(url)
    if res.status_code != 200:
        print(f"error: request to {url} responded with status: {res.status_code}")
        return None
    # Parse page
    page = BeautifulSoup(res.text, 'html.parser')
    manga_found = page.find_all(class_ = 'story_item')
    # No manga was found
    if len(manga_found) == 0:
        print(f"error: no manga was found with the search term '{manga_name}'")
        return None
    # Prompt for matches
    manga_choice = 0
    manga_extract_title = lambda element: element.find('h3', class_ = 'story_name').text.strip()
    if len(manga_found) > 1:
        print(f"notice: {len(manga_found)} matches were found")
        for index, manga_entry in enumerate(manga_found):
            manga_title = manga_extract_title(manga_entry)
            print(f"\t[{index}]\t{manga_title}")
        manga_choice = int(input("Please choose by typing the number: "))
    # Display selected entry
    manga_found_title = manga_extract_title(manga_found[manga_choice])
    print(f"notice: selected '{manga_found_title}'")
    # Extract manga id from entry
    manga_link = manga_found[manga_choice].find('a').get('href')
    manga_id = manga_link.split('-')[-1]
    print(f"notice: found corresponding manga id {manga_id}")
    return manga_id, manga_found_title

def manga_get_chapters(manga_id, lower_bound = None, upper_bound = None):
    if manga_id == "" or manga_id is None:
        print("error: cannot get chapters of invalid manga")
        return []
    url = url_join(MANGA_URL, f"manga-{url_quote(manga_id)}")
    res = fetch(url)
    if res.status_code != 200:
        print(f"error: request to {url} responded with status: {res.status_code}")
        return []
    page = BeautifulSoup(res.text, 'html.parser')
    links = page.find(class_ = 'chapter-list').find_all('a')
    chapters = map(lambda link: float(link.get('href').split('-')[-1]), links)
    if lower_bound is None:
        lower_bound = "0"
    if float(lower_bound) >= 0:
        chapters = filter(lambda chapter: chapter >= float(lower_bound), chapters)
    if upper_bound is not None and float(upper_bound) >= float(lower_bound):
        chapters = filter(lambda chapter: chapter <= float(upper_bound), chapters)
    chapters = list(chapters)
    chapters.sort()
    chapters = list(map(lambda chapter: str(chapter).rstrip('0').rstrip('.'), chapters))
    print(f"notice: found {len(chapters)} chapters")
    return (chapters)

def manga_chapter_get_images(manga_id, chapter_id):
    if manga_id == "" or manga_id is None:
        print("error: cannot get chapters of invalid manga")
        return []
    if chapter_id == "" or chapter_id is None:
        print("error: cannot get chapters of invalid chapter")
        return []
    url = url_join(CHAPTER_URL, f"manga-{url_quote(manga_id)}/chapter-{url_quote(chapter_id)}")
    res = fetch(url)
    if res.status_code != 200:
        print(f"error: request to {url} responded with status: {res.status_code}")
        return []
    page = BeautifulSoup(res.text, 'html.parser')
    vungdoc = page.find(id = 'vungdoc')
    image_elements = vungdoc.find_all('img')
    image_links = list(map(lambda element: element.get('data-src'), image_elements))
    print(f"notice: chapter {chapter_id} has {len(image_links)} images")
    return image_links

def manga_chapter_images_download(manga_title, chapter_id, image_urls):
    directory = Path(f"{manga_title}/chapter_{chapter_id}/")
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"notice: directory '{directory}' has been created")
    def image_download(url, path):
        res = fetch(url)
        if res.status_code != 200:
            print("error: could not download image at '{url}'")
            return
        with open(path, "wb") as file:
            file.write(res.content)
    threads = [
        Thread(
            target = image_download,
            args=(url, directory.joinpath(f"image_{idx}.jpg"))
        ) for idx, url in enumerate(image_urls)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

def main():
    args = args_get()
    manga_id, manga_title = manga_get_id_and_title(args.manga_name)
    manga_chapters = manga_get_chapters(manga_id, args.begin, args.end)
    for chapter_id in manga_chapters:
        images = manga_chapter_get_images(manga_id, chapter_id)
        if len(images) == 0:
            break
        manga_chapter_images_download(manga_title, chapter_id, images)

if __name__ == "__main__":
    main()
