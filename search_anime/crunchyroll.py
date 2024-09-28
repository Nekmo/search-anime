import uuid
from typing import Self, TypedDict, cast, Optional

import aiohttp

LOCALE = "es-ES"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/58.0.3029.110 Safari/537.3")
API_BASE_URL = "https://www.crunchyroll.com"
# API_BASE_URL = "http://localhost:8000"
API_GET_TOKEN_PATH = "/auth/v1/token"
API_GET_CONTENT_SEARCH_PATH = "/content/v2/discover/search"


class Authentication(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    country: str


class Crunchyroll:
    base_url = API_BASE_URL
    _authentication: Optional[Authentication] = None

    def __init__(self):
        pass

    def get_url(self, path):
        return f"{self.base_url}{path}"

    async def __aenter__(self) -> Self:
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.session.close()

    async def authenticate(self) -> Authentication:
        headers = await self.get_headers(False)
        headers["Authorization"] = "Basic Y3Jfd2ViOg=="
        headers["ETP-Anonymous-ID"] = uuid.uuid4().hex
        headers["content-type"] = "application/x-www-form-urlencoded"
        data = {"grant_type": "client_id"}
        async with self.session.post(self.get_url(API_GET_TOKEN_PATH), headers=headers, data=data) as response:
            response.raise_for_status()
            return cast(Authentication, await response.json())

    async def get_headers(self, auth: bool = True) -> dict:
        if auth and not self._authentication:
            self._authentication = await self.authenticate()
        headers = {
            "User-Agent": USER_AGENT,
        }
        if auth:
            headers["Authorization"] = f"{self._authentication['token_type']} {self._authentication['access_token']}"
        return headers

    async def search(self, query: str):
        params = {
            "q": query,
            "n": 6,
            "type": "music,series,episode,top_results,movie_listing",
            "ratings": "true",
            "preferred_audio_language": LOCALE,
            "locale": LOCALE,
        }
        async with self.session.get(self.get_url(API_GET_CONTENT_SEARCH_PATH), params=params,
                                    headers=(await self.get_headers())) as response:
            response.raise_for_status()
            await response.text()
            return await response.json()


async def main(query: str):
    async with Crunchyroll() as crunchyroll:
        anime = await crunchyroll.search(query)
        print(anime)


if __name__ == "__main__":
    import asyncio
    import sys

    asyncio.run(main(sys.argv[1]))
