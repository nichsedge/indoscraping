from .jenius import JeniusScraper
from .jago import JagoScraper
from .seabank import SeaBankScraper
from .blu import BluScraper
from .linebank import LineBankScraper
from .neobank import NeoBankScraper
from .krom import KromScraper
from .superbank import SuperbankScraper

ALL_SCRAPERS = [
    JeniusScraper,
    JagoScraper,
    SeaBankScraper,
    BluScraper,
    LineBankScraper,
    NeoBankScraper,
    KromScraper,
    SuperbankScraper
]
