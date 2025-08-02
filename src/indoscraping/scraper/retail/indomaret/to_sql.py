import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

# Load and clean data
df = pd.read_json("klikindomaret_products.json")

df.drop(
    ["descriptionList", "promoTagList", "promo", "promoText", "pairProducts"],
    axis=1,
    inplace=True,
    errors="ignore",
)

# Optionally save to CSV
df.to_csv("indomaret.csv", index=False)

# Create engine using the full DATABASE_URL from .env
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

# Write to PostgreSQL
df.to_sql(
    name="indomaret",
    con=engine,
    schema="public",
    if_exists="replace",
    method="multi",
    index=False,
)
