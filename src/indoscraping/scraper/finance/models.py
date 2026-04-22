from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RateDetail(BaseModel):
    tenor: str  # e.g., "1 month", "3 months", "daily"
    rate: float # interest rate in percentage
    min_balance: Optional[float] = None
    max_balance: Optional[float] = None
    extra_info: Optional[str] = None

class BankData(BaseModel):
    bank_name: str
    product_name: str # e.g., "Maxi Saver", "Deposito Jago"
    rates: List[RateDetail]
    last_updated: datetime = Field(default_factory=datetime.now)
    source_url: str

class ScrapeResult(BaseModel):
    banks: List[BankData]
    timestamp: datetime = Field(default_factory=datetime.now)
