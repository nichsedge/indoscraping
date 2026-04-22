from .base import ScrapeRunResult, UnsupportedSourceError


class BluScraper:
    mode = "http"

    def __init__(self):
        self.name = "blu by BCA Digital"
        self.url = "https://blubybcadigital.id/info/fees-rates"

    async def run(self, playwright) -> ScrapeRunResult:
        return ScrapeRunResult(
            scraper_name=self.name,
            source_url=self.url,
            mode=self.mode,
            error=UnsupportedSourceError(
                "blu by BCA Digital does not expose a stable official rates page "
                "that this scraper can parse reliably yet.",
                source_url=self.url,
            ),
        )
