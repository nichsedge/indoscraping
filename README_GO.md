# IndoScraping (Go Edition)

Native, high-performance Go migration running alongside the existing Python implementation. Specifically tailored to run flawlessly on native Android Termux (aarch64) as well as Linux containers and servers.

## 🚀 Key Features

* **Zero Python/glibc Bottlenecks**: Compiles to a single native binary on ARM64 Termux without wheel or Rust compiler compilation issues.
* **Direct Chromium Browser & Mobile Gateway Automation**: Bypasses bot checks using native discovery endpoints, SSR state extraction, and Chrome CDP integration.
* **Managed Goroutine Pool (`run all`)**: Runs all 10 scrapers concurrently with a controlled worker semaphore pool, completing multi-source crawls across news, e-commerce, and real estate in ~3 seconds.
* **Export to CSV**: Automatically transforms all JSON datasets into CSV files with a single command.
* **100% Format Compatibility**: Emits standard `latest.json`, `history/YYYY-MM-DD.json`, and `.meta.json` sidecar files identical to the Python suite.

---

## 🛠️ Usage

### Build the Binary
```bash
go build -o bin/indoscraping ./cmd/indoscraping
```

### Inspect Available Scrapers
```bash
./bin/indoscraping list
```

### Run Scrapers Individually
```bash
# News Scrapers
./bin/indoscraping run detik --limit-articles 5
./bin/indoscraping run cnbc --limit-articles 5
./bin/indoscraping run cnn --limit-articles 5
./bin/indoscraping run kompas --limit-articles 5

# E-Commerce & Retail (All Tested & Verified)
./bin/indoscraping run alfagift --query susu --limit-products 5
./bin/indoscraping run blibli --query kopi --limit-products 5
./bin/indoscraping run tokopedia --query kopi --limit-products 5
./bin/indoscraping run indomaret --query kopi --limit-products 5

# Real Estate & Boarding Houses (Kost)
./bin/indoscraping run jendela360 --limit-pages 1
./bin/indoscraping run sewakost --area jakarta/jakarta-barat/palmerah --limit-pages 1
```

### Run All Scrapers in Parallel
```bash
./bin/indoscraping run all --limit-items 5
```

### Export Datasets to CSV
```bash
# Export all datasets in data/ to CSV
./bin/indoscraping export csv

# Export a specific JSON dataset
./bin/indoscraping export data/ecommerce/tokopedia/latest.json
```

### Check Datasets & Storage Metrics
```bash
./bin/indoscraping status
```

---

## 🌐 Platform Discovery & Workaround Engineering

| Platform | Target | Method / Workaround Discovered | Speed |
| :--- | :--- | :--- | :--- |
| **Alfagift** | Grocery & Fresh | Direct Geo-coordinate injection (`-6.175, 106.827`) to `webcommerce-gw.alfagift.id` | ~300ms |
| **Blibli** | General E-Commerce | Mobile web backend gateway (`/backend/search/products?channelId=mobile-web`) bypassing Cloudflare Turnstile | ~400ms |
| **Tokopedia** | General E-Commerce | Server-Side Rendered (SSR) search state parser (`window.__cache`) bypassing Akamai GQL stream resets | ~1.2s |
| **Klik Indomaret**| Groceries & Essentials | Catalog Xpress webapp gateway (`ap-mc.klikindomaret.com`) with automated device headers | ~500ms |
| **Jendela360** | Apartments & Rentals | Jendela360 catalog API with IDR pricing, tower, and area metrics | ~1.5s |
| **SewaKost** | Kost & Boarding Rooms | Palmerah & Jakarta regional index parser with price & room tags | ~350ms |
| **Detik / CNBC / CNN / Kompas** | Indonesian News | Clean semantic DOM parsing with isolated metadata and dates | ~400ms |
