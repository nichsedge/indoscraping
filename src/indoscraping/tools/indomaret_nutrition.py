from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from rapidocr_onnxruntime import RapidOCR


NUTRI_PATTERNS = {
    # Indonesian / English label keywords
    "energi": re.compile(r"(?i)\benergi\b|\benergy\b"),
    "kalori": re.compile(r"(?i)\bkalori\b"),
    "protein": re.compile(r"(?i)\bprotein\b"),
    "lemak": re.compile(r"(?i)\blemak\b|\bfat\b"),
    "karbo": re.compile(r"(?i)\bkarbo(hidrat)?\b|\bcarb(ohydrate)?s?\b"),
    "gula": re.compile(r"(?i)\bgula\b|\bsugar\b"),
    "natrium": re.compile(r"(?i)\bnatrium\b|\bsodium\b"),
    "serat": re.compile(r"(?i)\bserat\b|\bfiber\b"),
    "akg": re.compile(r"(?i)\bAKG\b|\b%DV\b|\bdaily\s+value\b"),
    "kcal": re.compile(r"(?i)\bkkal\b|\bkcal\b"),
    "takaran_saji": re.compile(r"(?i)takaran\s+saji|serving\s+size"),
    "jumlah_sajian": re.compile(r"(?i)jumlah\s+sajian|servings\s+per"),
    "informasi_gizi": re.compile(r"(?i)informasi\s+(nilai\s+)?gizi|nutrition\s+facts"),
}

# Loose numeric extractors (OCR can be messy). We intentionally keep these very specific
# to avoid accidentally capturing unrelated numbers (e.g., %AKG, serving counts, product codes).
RE_CAL = re.compile(r"(?is)energi\s*total\s*(\d{1,4}(?:[\.,]\d{1,2})?)\s*(kkal|kcal)")
RE_PROTEIN = re.compile(r"(?is)protein\s*(\d{1,4}(?:[\.,]\d{1,2})?)\s*g")
RE_FAT = re.compile(r"(?is)lemak\s*total\s*(\d{1,4}(?:[\.,]\d{1,2})?)\s*g")
RE_CARBS = re.compile(r"(?is)karbohidrat\s*total\s*(\d{1,4}(?:[\.,]\d{1,2})?)\s*g")
RE_SUGAR = re.compile(r"(?is)gula\s*total\s*(\d{1,4}(?:[\.,]\d{1,2})?)\s*g")
RE_SODIUM = re.compile(r"(?is)(natrium|sodium)\D{0,20}(\d{1,4}(?:[\.,]\d{1,2})?)\s*mg")


@dataclass
class NutritionHit:
    productId: int
    plu: str
    permalink: str
    productName: str
    image_url: str
    image_file: str
    matched_keywords: List[str]
    # Parsed numeric fields when detectable
    calories_kcal: float | None
    protein_g: float | None
    fat_g: float | None
    carbs_g: float | None
    sugar_g: float | None
    sodium_mg: float | None
    ocr_text: str


def _safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")
    return s[:180] or "item"


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def iter_candidate_images(item: Dict[str, Any], *, max_images_per_product: int) -> List[str]:
    """Return a prioritized list of image URLs.

    Heuristic: later numbered images often include nutrition/back label.
    We'll try all, but prefer non-thumb and higher suffixes.
    """

    imgs: List[str] = []

    for k in ("images",):
        v = item.get(k)
        if isinstance(v, list):
            imgs.extend([x for x in v if isinstance(x, str) and x.startswith("http")])

    for k in ("imageUrl", "thumbnail"):
        v = item.get(k)
        if isinstance(v, str) and v.startswith("http"):
            imgs.append(v)

    # de-dupe while preserving order
    seen = set()
    uniq = []
    for u in imgs:
        if u not in seen:
            seen.add(u)
            uniq.append(u)

    def score(u: str) -> Tuple[int, int]:
        # higher is better
        is_thumb = 1 if "thumb" in u else 0
        m = re.search(r"_(\d+)\.jpg$", u)
        idx = int(m.group(1)) if m else 0
        return (-is_thumb, idx)

    uniq.sort(key=score, reverse=True)
    return uniq[:max_images_per_product]


def download_image(client: httpx.Client, url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = os.path.splitext(url.split("?")[0])[1]
    if suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    fname = f"{_hash_url(url)}{suffix}"
    path = out_dir / fname
    if path.exists() and path.stat().st_size > 0:
        return path

    r = client.get(url, timeout=30)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def ocr_image(ocr: RapidOCR, image_path: Path) -> str:
    # RapidOCR returns: (result, elapse)
    res, _ = ocr(str(image_path))
    if not res:
        return ""
    # res: List[[box, text, score], ...]
    lines = [x[1] for x in res if len(x) >= 2 and isinstance(x[1], str)]
    return "\n".join(lines)


def matched_keywords(text: str) -> List[str]:
    hits = []
    for name, pat in NUTRI_PATTERNS.items():
        if pat.search(text or ""):
            hits.append(name)
    return hits


def _to_float(s: str) -> float | None:
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None


def parse_nutrition_numbers(text: str) -> Dict[str, float | None]:
    """Best-effort numeric extraction from OCR text."""

    out: Dict[str, float | None] = {
        "calories_kcal": None,
        "protein_g": None,
        "fat_g": None,
        "carbs_g": None,
        "sugar_g": None,
        "sodium_mg": None,
    }

    if not text:
        return out

    m = RE_CAL.search(text)
    if m:
        out["calories_kcal"] = _to_float(m.group(1))

    m = RE_PROTEIN.search(text)
    if m:
        out["protein_g"] = _to_float(m.group(1))

    m = RE_FAT.search(text)
    if m:
        out["fat_g"] = _to_float(m.group(1))

    m = RE_CARBS.search(text)
    if m:
        out["carbs_g"] = _to_float(m.group(1))

    m = RE_SUGAR.search(text)
    if m:
        out["sugar_g"] = _to_float(m.group(1))

    m = RE_SODIUM.search(text)
    if m:
        # sodium regex has 2 capture groups: label + number
        out["sodium_mg"] = _to_float(m.group(2))

    return out


def load_products(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}, got {type(data).__name__}")
    return [x for x in data if isinstance(x, dict)]


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract nutrition facts candidates from Indomaret dataset via OCR of product images.")
    ap.add_argument("--input", default="data/ecommerce/indomaret/latest.dedup.json", help="Input product JSON (default: latest.dedup.json)")
    ap.add_argument("--out", default="data/ecommerce/indomaret/nutrition/nutrition_hits.jsonl", help="Output JSONL path")
    ap.add_argument("--download-dir", default="data/ecommerce/indomaret/nutrition/images", help="Where to store downloaded images")
    ap.add_argument("--max-products", type=int, default=300, help="Max products to scan (OCR is expensive). Use 0 for all.")
    ap.add_argument("--max-images-per-product", type=int, default=4, help="Limit images tried per product.")
    ap.add_argument("--min-keywords", type=int, default=2, help="How many nutrition keywords must match to keep a hit.")
    ap.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between downloads to be polite.")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.out)
    img_dir = Path(args.download_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    products = load_products(in_path)
    if args.max_products and args.max_products > 0:
        products = products[: args.max_products]

    ocr = RapidOCR()

    client = httpx.Client(headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)

    kept = 0
    scanned_imgs = 0

    with out_path.open("w", encoding="utf-8") as f_out:
        for i, it in enumerate(products, 1):
            pid = it.get("productId")
            plu = str(it.get("plu") or "")
            permalink = str(it.get("permalink") or "")
            pname = str(it.get("productName") or "")

            if pid is None:
                continue

            urls = iter_candidate_images(it, max_images_per_product=args.max_images_per_product)
            if not urls:
                continue

            for url in urls:
                scanned_imgs += 1
                try:
                    img_path = download_image(client, url, img_dir)
                    text = ocr_image(ocr, img_path)
                    kws = matched_keywords(text)
                    nums = parse_nutrition_numbers(text)

                    # keep if keyword hits OR any numeric nutrition parsed
                    keep = (len(kws) >= args.min_keywords) or any(v is not None for v in nums.values())

                    if keep:
                        hit = NutritionHit(
                            productId=int(pid),
                            plu=plu,
                            permalink=permalink,
                            productName=pname,
                            image_url=url,
                            image_file=str(img_path),
                            matched_keywords=sorted(kws),
                            calories_kcal=nums["calories_kcal"],
                            protein_g=nums["protein_g"],
                            fat_g=nums["fat_g"],
                            carbs_g=nums["carbs_g"],
                            sugar_g=nums["sugar_g"],
                            sodium_mg=nums["sodium_mg"],
                            ocr_text=text,
                        )
                        f_out.write(json.dumps(hit.__dict__, ensure_ascii=False) + "\n")
                        # flush so partial results survive timeouts/interrupts
                        f_out.flush()
                        kept += 1

                except Exception as e:
                    # Keep going; OCR pipelines are noisy.
                    continue

                if args.sleep:
                    time.sleep(args.sleep)

            if i % 25 == 0:
                print(f"processed_products={i} kept_hits={kept} scanned_images={scanned_imgs}")

    print(f"DONE: wrote {kept} nutrition-candidate hits to {out_path}")


if __name__ == "__main__":
    main()
