from pathlib import Path
import pandas as pd
import json

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "ecommerce" / "indomaret" / "nutrition"

# Read the CSV
df = pd.read_csv(DATA_DIR / "indomaret_nutrition_facts.csv")
print(f"Shape: {df.shape}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nDtypes:\n{df.dtypes}")
print(f"\nMissing values:\n{df.isnull().sum()}")
print(f"\nSample rows:")
print(df.head(10).to_string())

# Stats on nutrition columns
nutri_cols = ['calories_kcal', 'protein_g', 'fat_g', 'carbs_g', 'sugar_g', 'sodium_mg']
print(f"\n\nNutrition stats:")
print(df[nutri_cols].describe())

# Count products with complete nutrition info
complete = df[nutri_cols].notna().all(axis=1).sum()
print(f"\nProducts with complete nutrition info: {complete}/{len(df)}")

# Products with at least calories
has_calories = df['calories_kcal'].notna().sum()
print(f"Products with calories: {has_calories}/{len(df)}")

# Category analysis from product names
df['category'] = df['productName'].str.extract(r'(Susu|Kecap|Biskuit|Bubur|Snack|Pasta|Sup|Keju|Bumbu|Minuman|Cokelat|Melty|Puding|Cereal|Royco|Yogurt)', expand=False)
print(f"\nCategories found:")
print(df['category'].value_counts(dropna=False))