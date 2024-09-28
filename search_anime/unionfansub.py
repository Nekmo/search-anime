import os
import sys
from typing import Self, TypedDict, Tuple, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

BASE_URL = "https://foro.unionfansub.com"
LOGIN_URL = BASE_URL + "/member.php"
UPLOADING_URL = BASE_URL + "/announcements.php?aid=14"
UPLOADS_URL = BASE_URL + "/anime.php"


class UnionFansubAnime(TypedDict):
    title: str
    url: str
    fansub: str
    source: Optional[str]
    resolution: Optional[str]
    audios: Optional[list[str]]
    subtitles: Optional[list[str]]
    episodes: Optional[int]
    servers: Optional[list[str]]
    seeders: Optional[int]
    leechers: Optional[int]
    is_recommended: Optional[bool]


class UnionFansub:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    async def __aenter__(self) -> Self:
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.session.close()

    async def login(self):
        data = {
            'action': 'do_login',
            'username': self.username,
            'password': self.password,
        }
        async with self.session.post(LOGIN_URL, data=data) as response:
            response.raise_for_status()
            text = await response.text()
            if "Has iniciado sesión correctamente." not in text:
                raise ValueError("Login failed.")

    async def search_uploaded(self, query: str) -> Tuple[Optional[UnionFansubAnime], int]:
        async with self.session.post(UPLOADS_URL, data={"nombre": query}) as response:
            response.raise_for_status()
            soup = BeautifulSoup(await response.text(), "html.parser")
            trows = soup.find_all("tr", class_="trow2")
        best_anime = None
        ratio = 0
        for trow in trows:
            tds = trow.find_all("td")
            if not tds:
                continue
            anime = {
                "title": tds[0].text,
                "url": urljoin(BASE_URL, tds[0].find("a").attrs["href"]),
                "fansub": tds[1].text,
                "source": tds[2].find("span", class_="source").attrs["title"],
                "resolution": tds[2].find("span", class_="resolucion").text,
                "audios": [x.attrs["title"] for x in tds[3].find("span")],
                "subtitles": [x.attrs["title"] for x in (tds[4].find("span") or [])],
                "episodes": tds[5].text,
                "servers": [x.attrs["title"] for x in (tds[6].find("span") or [])],
                "seeders": int(tds[7].text.split("/", 1)[0].strip()) if tds[7].text else 0,
                "leechers": int(tds[7].text.split("/", 1)[1].strip()) if tds[7].text else 0,
                "is_recommend": "recomendado" in trow.attrs["class"]
            }
            anime_ratio = fuzz.ratio(query, anime["title"])
            if anime_ratio > ratio or (anime_ratio == ratio and anime["is_recommend"]):
                best_anime = anime
                ratio = anime_ratio
        return best_anime, ratio

    async def search_uploading(self, query: str) -> Tuple[Optional[UnionFansubAnime], int]:
        async with self.session.get(UPLOADING_URL) as response:
            response.raise_for_status()
            soup = BeautifulSoup(await response.text(), "html.parser")
            divs = soup.find("div", class_="listado").find_all("div")
        best_anime = None
        ratio = 0
        for div in divs:
            anime = {
                "title": div.find("a").text,
                "url": urljoin(BASE_URL, div.find("a").attrs["href"]),
                "fansub": div.find('span').find(string=True, recursive=False),
            }
            anime_ratio = fuzz.ratio(query, anime["title"])
            if anime_ratio > ratio:
                best_anime = anime
                ratio = anime_ratio
        return best_anime, ratio

    async def search(self, query: str) -> Optional[UnionFansubAnime]:
        uploaded_anime, uploaded_ratio = await self.search_uploaded(query)
        uploading_anime, uploading_ratio = await self.search_uploading(query)
        if uploaded_ratio > uploading_ratio:
            return uploaded_anime
        return uploading_anime


async def main(query: str):
    async with UnionFansub(os.environ["UNIONFANSUB_USERNAME"], os.environ["UNIONFANSUB_PASSWORD"]) as unionfansub:
        await unionfansub.login()
        anime = await unionfansub.search(query)
        print(anime)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(sys.argv[1]))
