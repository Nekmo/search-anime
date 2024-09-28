import sys
from typing import Self, List, TypedDict, Optional

import aiohttp
from aiohttp import ClientResponse
from bs4 import BeautifulSoup, Tag

URL = "https://myanimelist.net"
DEMOGRAPHIC = {"Shounen": "Shonen", "Shoujo": "Shojo", "Kids": "Kodomo"}


class MyAnimeListAnime(TypedDict):
    id: int
    name: str
    image_url: str
    es_score: float
    media_type: str
    score: str
    start_year: int
    status: str
    url: str
    episodes: Optional[int]
    duration: str
    demographic: str
    genres: List[str]
    themes: List[str]
    producers: List[str]
    studios: List[str]


class MyAnimeListSearchItemPayload(TypedDict):
    aired: str
    media_type: str
    score: str
    start_year: int
    status: str


class MyAnimeListSearchItem(TypedDict):
    es_score: float
    id: int
    image_url: str
    name: str
    payload: MyAnimeListSearchItemPayload
    thumbnail_url: str
    type: str
    url: str


def parse_info(tag: Tag, string: str) -> Optional[Tag]:
    item = tag.find("span", class_="dark_text", string=string)
    if item:
        return item.parent


def parse_info_text(tag: Tag, string: str):
    item = parse_info(tag, string)
    if item:
        return list(item.strings)[-1].strip()


def parse_url_items(tag, string):
    item = parse_info(tag, string)
    if item:
        return [x.text for x in item.find_all("a")]


class MyAnimeList:
    def __init__(self):
        pass

    async def __aenter__(self) -> Self:
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.session.close()

    @property
    def url(self):
        url = URL
        if not url.endswith("/"):
            url = f"{url}/"
        return url

    async def _retrieve(self, path, **kwargs) -> ClientResponse:
        url = f"{self.url}{path}"
        async with self.session.get(url, **kwargs) as response:
            response.raise_for_status()
            await response.text()
            return response

    async def search(self, query: str) -> MyAnimeListAnime:
        api_response = await self._retrieve(
            "search/prefix.json", params={"type": "anime", "keyword": query, "v": "1"}
        )
        api_data = await api_response.json()
        api_animes = next(filter(lambda x: x["type"] == "anime", api_data["categories"]))["items"]
        if not api_animes:
            raise ValueError("No anime found.")
        anime: MyAnimeListSearchItem = api_animes[0]
        anime_response = await self._retrieve(anime["url"].replace(self.url, ""))
        soup = BeautifulSoup(await anime_response.text(), "html.parser")
        leftside = soup.select_one(".leftside")
        episodes = parse_info_text(leftside, "Episodes:")
        duration = parse_info_text(leftside, "Duration:")
        demographic = parse_url_items(leftside, "Demographic:")
        genres = parse_url_items(leftside, "Genre:") or parse_url_items(leftside, "Genres:")
        themes = parse_url_items(leftside, "Theme:") or parse_url_items(leftside, "Themes:")
        producers = parse_url_items(leftside, "Producer:") or parse_url_items(leftside, "Producers:")
        studios = parse_url_items(leftside, "Studio:") or parse_url_items(leftside, "Studios:")
        image_url = anime["image_url"].replace("r/116x180/", "").split("?")[0].replace(".jpg", "l.jpg")
        return {
            "id": anime["id"],
            "name": anime["name"],
            "image_url": image_url,
            "es_score": anime["es_score"],
            "media_type": anime["payload"]["media_type"],
            "score": anime["payload"]["score"],
            "start_year": anime["payload"]["start_year"],
            "status": anime["payload"]["status"],
            "url": anime["url"],
            "episodes": int(episodes) if episodes.isdigit() else None,
            "duration": duration.replace(" per ep.", ""),
            "demographic": DEMOGRAPHIC.get(demographic[0], demographic[0]) if demographic else None,
            "genres": genres or [],
            "themes": themes or [],
            "producers": producers,
            "studios": studios,
        }


async def main(query: str):
    async with MyAnimeList() as mal:
        anime = await mal.search(query)
        print(anime)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(sys.argv[1]))
