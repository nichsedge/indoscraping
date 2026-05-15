import abc
import json
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

import requests
from bs4 import BeautifulSoup
from playwright.async_api import Page
from playwright_stealth import Stealth

from .models import BankData


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
    "image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": DEFAULT_USER_AGENT,
}


class ScraperError(Exception):
    code = "scraper_error"

    def __init__(self, message: str, *, source_url: str | None = None):
        super().__init__(message)
        self.message = message
        self.source_url = source_url


class BlockedError(ScraperError):
    code = "blocked"


class SourceChangedError(ScraperError):
    code = "source_changed"


class EmptyParseError(ScraperError):
    code = "empty_parse"


class UnsupportedSourceError(ScraperError):
    code = "unsupported"


@dataclass
class ScrapeRunResult:
    scraper_name: str
    source_url: str
    mode: str
    bank_data: list[BankData] = field(default_factory=list)
    error: ScraperError | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class BaseScraper(abc.ABC):
    mode: ClassVar[str] = "http"
    request_timeout: ClassVar[int] = 30

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    async def run(self, playwright) -> ScrapeRunResult:
        try:
            if self.mode == "http":
                data = self.scrape_http(self.fetch_document(self.url))
            elif self.mode == "browser":
                data = await self.scrape_with_browser(playwright)
            elif self.mode == "hybrid":
                try:
                    data = self.scrape_http(self.fetch_document(self.url))
                except ScraperError:
                    data = await self.scrape_with_browser(playwright)
            else:
                raise UnsupportedSourceError(
                    f"Unknown scraper mode: {self.mode}", source_url=self.url
                )

            if not data:
                raise EmptyParseError(
                    f"{self.name} returned no data", source_url=self.url
                )

            return ScrapeRunResult(
                scraper_name=self.name,
                source_url=self.url,
                mode=self.mode,
                bank_data=data,
            )
        except ScraperError as exc:
            return ScrapeRunResult(
                scraper_name=self.name,
                source_url=exc.source_url or self.url,
                mode=self.mode,
                error=exc,
            )
        except Exception as exc:
            return ScrapeRunResult(
                scraper_name=self.name,
                source_url=self.url,
                mode=self.mode,
                error=ScraperError(str(exc), source_url=self.url),
            )

    def fetch_document(self, url: str) -> BeautifulSoup:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.request_timeout)

        if self.response_is_blocked(response.status_code, response.text):
            raise BlockedError(
                f"{self.name} blocked the request with status {response.status_code}",
                source_url=url,
            )

        if response.status_code >= 400:
            raise SourceChangedError(
                f"{self.name} returned HTTP {response.status_code}",
                source_url=url,
            )

        return BeautifulSoup(response.text, "html.parser")

    async def scrape_with_browser(self, playwright) -> list[BankData]:
        browser = await playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            viewport={"width": 1440, "height": 900},
            user_agent=DEFAULT_USER_AGENT,
            java_script_enabled=True,
        )
        await context.set_extra_http_headers(
            {
                "Accept-Language": DEFAULT_HEADERS["Accept-Language"],
                "Upgrade-Insecure-Requests": "1",
            }
        )

        try:
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            html = await page.content()
            if self.response_is_blocked(await page.title(), html):
                raise BlockedError(
                    f"{self.name} browser session was blocked", source_url=self.url
                )
            return await self.scrape_browser(page, html)
        finally:
            await context.close()
            await browser.close()

    def response_is_blocked(self, status_or_title: int | str, text: str) -> bool:
        haystack = text.lower()
        if isinstance(status_or_title, int) and status_or_title in {401, 403, 429}:
            return True
        title = str(status_or_title).lower()
        blocked_markers = (
            "attention required",
            "please enable cookies",
            "sorry, you have been blocked",
            "access denied",
            "cf-challenge",
        )
        return any(marker in title or marker in haystack for marker in blocked_markers)

    def scrape_http(self, soup: BeautifulSoup) -> list[BankData]:
        raise UnsupportedSourceError(
            f"{self.name} does not implement HTTP scraping", source_url=self.url
        )

    async def scrape_browser(self, page: Page, html: str) -> list[BankData]:
        raise UnsupportedSourceError(
            f"{self.name} does not implement browser scraping", source_url=self.url
        )


def extract_next_data(soup: BeautifulSoup) -> dict[str, Any]:
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        raise SourceChangedError("Missing __NEXT_DATA__ payload")
    return json.loads(script.string)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_rate(value: str) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", value)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def collect_strings(node: Any) -> list[str]:
    values: list[str] = []
    if isinstance(node, str):
        values.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            values.extend(collect_strings(value))
    elif isinstance(node, list):
        for value in node:
            values.extend(collect_strings(value))
    return values


_SECTION_TERMINATOR_RE = re.compile(
    r"(?P<body>.*?)(?:\n\d+\)\s|\n[A-Z]\.\s|$)",
    re.IGNORECASE | re.DOTALL,
)


def find_table_after_label(text: str, label: str) -> str:
    match = re.search(re.escape(label), text, re.IGNORECASE)
    if not match:
        raise SourceChangedError(f"Could not find section {label!r}")

    match_body = _SECTION_TERMINATOR_RE.search(text, pos=match.end())
    if not match_body:
        raise SourceChangedError(f"Could not find end of section {label!r}")
    return match_body.group("body")
