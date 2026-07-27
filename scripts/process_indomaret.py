from pathlib import Path
import pandas as pd
import json

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "ecommerce" / "indomaret" / "nutrition"

# Read the CSV
df = pd.read_csv(DATA_DIR / "indomaret_nutrition_facts.csv")

# Nutrition columns
nutri_cols = ['calories_kcal', 'protein_g', 'fat_g', 'carbs_g', 'sugar_g', 'sodium_mg']

# Categorize products
def categorize(name):
    name_lower = name.lower()
    if any(k in name_lower for k in ['susu', 'formula', 'materna', 'pregnant', 'ibu hamil', 'lactogen', 'lactogrow', 'chilgo', 'frisian', 's-26', 'promil', 'preneg', 'bebelac', 'bebelove', 'morigro', 'sgm', 'eksplor', 'batita']):
        return 'Susu/Formula'
    elif 'kecap' in name_lower:
        return 'Kecap/Saus'
    elif any(k in name_lower for k in ['biskuit', 'biscuit', 'cookie']):
        return 'Biskuit'
    elif 'bubur' in name_lower:
        return 'Bubur Bayi'
    elif any(k in name_lower for k in ['snack', 'puffs', 'crackers', 'softcorn', 'melty', 'rice puffs']):
        return 'Snack Anak'
    elif 'pasta' in name_lower:
        return 'Pasta Bayi'
    elif 'sup' in name_lower or 'soup' in name_lower:
        return 'Sup Bayi'
    elif any(k in name_lower for k in ['keju', 'cheddar', 'cheese', 'wincheez', 'kraft']):
        return 'Keju'
    elif 'bumbu' in name_lower or 'royco' in name_lower:
        return 'Bumbu Instan'
    elif any(k in name_lower for k in ['milo', 'minuman', 'cokelat', 'chocolate']):
        return 'Minuman'
    elif 'puding' in name_lower or 'silky' in name_lower:
        return 'Puding'
    elif 'cereal' in name_lower:
        return 'Cereal'
    elif 'yogurt' in name_lower:
        return 'Yogurt'
    else:
        return 'Lainnya'

df['category'] = df['productName'].apply(categorize)

# Create serving size estimate from product name
def extract_serving(name):
    import re
    # Try to extract weight
    patterns = [
        r'(\d+(?:\.\d+)?)\s*[kK][gG]',
        r'(\d+(?:\.\d+)?)\s*[gG](?!\w)',
        r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*[gG]',
    ]
    for p in patterns:
        m = re.search(p, name)
        if m:
            if len(m.groups()) == 2:
                return f"{m.group(1)}x{m.group(2)}g"
            return f"{m.group(1)}g"
    return None

df['serving_size'] = df['productName'].apply(extract_serving)

# Output cleaned CSV
output_cols = ['productId', 'plu', 'productName', 'category', 'serving_size', 
               'calories_kcal', 'protein_g', 'fat_g', 'carbs_g', 'sugar_g', 'sodium_mg',
               'image_url', 'image_file']
df[output_cols].to_csv(DATA_DIR / 'indomaret_nutrition_clean.csv', index=False)
print(f"Cleaned CSV saved: {len(df)} rows")

# Output Parquet
df[output_cols].to_parquet(DATA_DIR / 'indomaret_nutrition_clean.parquet', index=False)
print("Parquet saved")

# Output SQLite
import sqlite3
conn = sqlite3.connect(DATA_DIR / 'indomaret_nutrition.db')
df[output_cols].to_sql('products', conn, if_exists='replace', index=False)
conn.close()
print("SQLite saved")

# Category summary
print("\n=== Category Summary ===")
cat_summary = df.groupby('category').agg(
    count=('productId', 'count'),
    with_calories=('calories_kcal', lambda x: x.notna().sum()),
    avg_calories=('calories_kcal', 'mean'),
    avg_protein=('protein_g', 'mean'),
    avg_fat=('fat_g', 'mean'),
    avg_carbs=('carbs_g', 'mean'),
    avg_sodium=('sodium_mg', 'mean')
).round(1)
print(cat_summary.to_string())

# Products with complete nutrition
complete = df[nutri_cols].notna().all(axis=1)
print(f"\n=== Products with COMPLETE nutrition ({complete.sum()}/{len(df)}) ===")
print(df[complete][['productName', 'category'] + nutri_cols].to_string(index=False))

# Products with only calories
only_cal = df['calories_kcal'].notna() & df['protein_g'].isna() & df['fat_g'].isna() & df['carbs_g'].isna()
print(f"\n=== Products with ONLY calories ({only_cal.sum()}) ===")
print(df[only_cal][['productName', 'category', 'calories_kcal']].to_string(index=False))

# Missing nutrition by category
print(f"\n=== Missing nutrition % by category ===")
for col in nutri_cols:
    miss = df.groupby('category')[col].apply(lambda x: x.isna().mean()*100).round(1)
    print(f"\n{col}:")
    print(miss.to_string())

# Export summary JSON
summary = {
    'total_products': int(len(df)),
    'products_with_calories': int(df['calories_kcal'].notna().sum()),
    'products_with_complete_nutrition': int(complete.sum()),
    'categories': df['category'].value_counts().to_dict(),
    'nutrition_coverage_pct': {col: round(df[col].notna().mean()*100, 1) for col in nutri_cols}
}
with open(DATA_DIR / 'indomaret_nutrition_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)
print("\nSummary JSON saved")