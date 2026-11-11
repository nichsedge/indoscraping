package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/nichsedge/indoscraping/pkg/browser"
	"github.com/nichsedge/indoscraping/pkg/core"
	"github.com/nichsedge/indoscraping/pkg/export"
	"github.com/nichsedge/indoscraping/pkg/scrapers/banking"
	"github.com/nichsedge/indoscraping/pkg/scrapers/ecommerce"
	"github.com/nichsedge/indoscraping/pkg/scrapers/hardware"
	"github.com/nichsedge/indoscraping/pkg/scrapers/news"
	"github.com/nichsedge/indoscraping/pkg/scrapers/property"
)

const (
	colorReset  = "\033[0m"
	colorRed    = "\033[31m"
	colorGreen  = "\033[32m"
	colorYellow = "\033[33m"
	colorBlue   = "\033[34m"
	colorPurple = "\033[35m"
	colorCyan   = "\033[36m"
	colorBold   = "\033[1m"
)

func printBanner() {
	fmt.Printf("%s%s", colorCyan, colorBold)
	fmt.Println(`
╔═══════════════════════════════════════════════════════════════╗
║                   INDOSCRAPING (Go Edition)                   ║
║   High-Performance Indonesian Web Scraper Suite & CLI         ║
╚═══════════════════════════════════════════════════════════════╝` + colorReset)
}

func main() {
	if len(os.Args) < 2 {
		printBanner()
		printUsage()
		return
	}

	command := os.Args[1]

	switch command {
	case "list":
		handleList()
	case "status":
		handleStatus()
	case "check-browser":
		handleCheckBrowser()
	case "bijak-beli":
		handleBijakBeli(os.Args[2:])
	case "best-bank", "banking":
		handleBestBank(os.Args[2:])
	case "export":
		handleExport(os.Args[2:])
	case "run":
		handleRun(os.Args[2:])
	default:
		printBanner()
		fmt.Printf("%sUnknown command: %s%s\n\n", colorRed, command, colorReset)
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Printf("%sUsage:%s\n", colorBold, colorReset)
	fmt.Println("  indoscraping <command> [options]")
	fmt.Println()
	fmt.Printf("%sCommands:%s\n", colorBold, colorReset)
	fmt.Printf("  %slist%s                 List all registered scrapers\n", colorGreen, colorReset)
	fmt.Printf("  %srun <scraper|all>%s    Execute a specific scraper or all concurrently\n", colorGreen, colorReset)
	fmt.Printf("  %sbijak-beli%s           Run cross-retailer consumer staples price index (Alfamart vs Indomaret)\n", colorGreen, colorReset)
	fmt.Printf("  %sbest-bank%s            Evaluate best Indonesian banks for retailers (rates, fees, QRIS, APY)\n", colorGreen, colorReset)
	fmt.Printf("  %sexport csv [path]%s    Export JSON datasets into CSV format\n", colorGreen, colorReset)
	fmt.Printf("  %sstatus%s               Check generated data metrics and files\n", colorGreen, colorReset)
	fmt.Printf("  %scheck-browser%s        Detect system Chromium and verify browser engine\n", colorGreen, colorReset)
	fmt.Println()
	fmt.Printf("%sExamples:%s\n", colorBold, colorReset)
	fmt.Println("  ./bin/indoscraping list")
	fmt.Println("  ./bin/indoscraping bijak-beli --limit-per-item 5")
	fmt.Println("  ./bin/indoscraping run passmark")
	fmt.Println("  ./bin/indoscraping run detik --limit-articles 5")
	fmt.Println("  ./bin/indoscraping run blibli --query kopi --limit-products 5")
	fmt.Println("  ./bin/indoscraping run alfagift --query susu --limit-products 5")
	fmt.Println("  ./bin/indoscraping run sewakost --area jakarta/jakarta-barat/palmerah --limit-pages 1")
	fmt.Println("  ./bin/indoscraping run all --limit-items 3")
	fmt.Println("  ./bin/indoscraping export csv")
	fmt.Println("  ./bin/indoscraping status")
}

type scraperInfo struct {
	Key      string
	Name     string
	Category string
	Engine   string
	Desc     string
}

var registry = []scraperInfo{
	{
		Key:      "detik",
		Name:     "Detik.com News Scraper",
		Category: "News",
		Engine:   "HTTP / HTML Parser",
		Desc:     "Scrapes breaking news and index articles from Detik.",
	},
	{
		Key:      "cnbc",
		Name:     "CNBC Indonesia Scraper",
		Category: "News",
		Engine:   "HTTP / HTML Parser",
		Desc:     "Extracts market and economics articles from CNBC Indonesia.",
	},
	{
		Key:      "cnn",
		Name:     "CNN Indonesia Scraper",
		Category: "News",
		Engine:   "HTTP / HTML Parser",
		Desc:     "Extracts national and regional articles from CNN Indonesia.",
	},
	{
		Key:      "kompas",
		Name:     "Kompas.com Scraper",
		Category: "News",
		Engine:   "HTTP / HTML Parser",
		Desc:     "Extracts national and regional articles from Kompas Indeks.",
	},
	{
		Key:      "alfagift",
		Name:     "Alfagift Scraper",
		Category: "E-Commerce",
		Engine:   "REST API (Geo-aware)",
		Desc:     "Fetches products, verified prices, and stock from Alfagift searches gateway.",
	},
	{
		Key:      "blibli",
		Name:     "Blibli Search Scraper",
		Category: "E-Commerce",
		Engine:   "Mobile Backend Gateway",
		Desc:     "High-speed discovery extractor for Blibli products, prices, and merchants.",
	},
	{
		Key:      "tokopedia",
		Name:     "Tokopedia Search Scraper",
		Category: "E-Commerce",
		Engine:   "SSR State Extractor",
		Desc:     "Extracts Tokopedia marketplace products, verified prices, sellers, and URLs.",
	},
	{
		Key:      "indomaret",
		Name:     "Klik Indomaret Scraper",
		Category: "E-Commerce",
		Engine:   "Catalog Xpress API",
		Desc:     "Extracts grocery products, discounted prices, UOM, and brands from Klik Indomaret.",
	},
	{
		Key:      "jendela360",
		Name:     "Jendela360 Property Scraper",
		Category: "Property",
		Engine:   "REST API",
		Desc:     "Extracts apartment & property listings with IDR rates from Jendela360.",
	},
	{
		Key:      "sewakost",
		Name:     "SewaKost Property Scraper",
		Category: "Property",
		Engine:   "HTTP / HTML Parser",
		Desc:     "Extracts boarding house & kost rental listings with room specs and prices.",
	},
	{
		Key:      "passmark",
		Name:     "PassMark Hardware Benchmarks",
		Category: "Hardware",
		Engine:   "HTTP / HTML Parser",
		Desc:     "Extracts live PassMark GPU (G3D Mark) and CPU compute ratings for price-to-performance analysis.",
	},
	{
		Key:      "banking",
		Name:     "Indonesian Banking & Rates",
		Category: "Banking",
		Engine:   "HTTP / Regulatory Aggregator",
		Desc:     "Scrapes SBDK lending rates, tiered savings APYs, fees, and evaluates best banks for retailers.",
	},
}

func handleList() {
	printBanner()
	fmt.Printf("%sAvailable Scrapers (%d total):%s\n\n", colorBold, len(registry), colorReset)

	fmt.Printf("%-12s %-28s %-15s %-25s %s\n", "KEY", "NAME", "CATEGORY", "ENGINE", "DESCRIPTION")
	fmt.Println(strings.Repeat("─", 110))

	for _, s := range registry {
		fmt.Printf("%s%-12s%s %-28s %s%-15s%s %s%-25s%s %s\n",
			colorYellow, s.Key, colorReset,
			s.Name,
			colorCyan, s.Category, colorReset,
			colorPurple, s.Engine, colorReset,
			s.Desc,
		)
	}
	fmt.Println()
}

func handleCheckBrowser() {
	printBanner()
	fmt.Println("🔍 Checking Chromium browser configuration...")
	path, err := browser.FindChromium()
	if err != nil {
		fmt.Printf("%s❌ Error:%s %v\n", colorRed, colorReset, err)
		return
	}
	fmt.Printf("%s✅ Browser Found:%s %s\n", colorGreen, colorReset, path)
	fmt.Printf("%s🚀 Status:%s Native Chromium is ready for Go chromedp browser scrapers!\n\n", colorGreen, colorReset)
}

func handleExport(args []string) {
	printBanner()
	fmt.Println("📦 Exporting Datasets to CSV...")

	var target string
	if len(args) > 0 {
		target = args[0]
	}

	if target != "" && strings.HasSuffix(target, ".json") {
		csvPath := strings.TrimSuffix(target, ".json") + ".csv"
		if err := export.JSONToCSV(target, csvPath); err != nil {
			fmt.Printf("%s❌ Error exporting %s: %v%s\n", colorRed, target, err, colorReset)
			return
		}
		fmt.Printf("%s✅ Exported:%s %s -> %s\n\n", colorGreen, colorReset, target, csvPath)
		return
	}

	exported, err := export.ExportAllToCSV("data")
	if err != nil {
		fmt.Printf("%s❌ Error walking data directory: %v%s\n", colorRed, err, colorReset)
		return
	}

	fmt.Printf("%s✅ Successfully exported %d dataset(s) to CSV:%s\n", colorGreen, len(exported), colorReset)
	for _, f := range exported {
		fmt.Printf(" • %s\n", f)
	}
	fmt.Println()
}

func handleBijakBeli(args []string) {
	printBanner()
	fs := flag.NewFlagSet("bijak-beli", flag.ExitOnError)
	limitPerItem := fs.Int("limit-per-item", 3, "Number of products per retailer per staple")
	queriesStr := fs.String("queries", "minyak,beras,susu,gula,telur,mie", "Comma-separated list of staple query keywords")
	outputPath := fs.String("output", "data/bijak_beli/latest.json", "Output JSON path")
	fs.Parse(args)

	fmt.Printf("%s🛒 [BIJAK-BELI]%s Initiating Consumer Staples Price Index Ingestion...\n", colorGreen, colorReset)
	fmt.Printf("   Queries: %s | Limit per staple: %d\n\n", *queriesStr, *limitPerItem)

	var queryList []string
	for _, q := range strings.Split(*queriesStr, ",") {
		q = strings.TrimSpace(q)
		if q != "" {
			queryList = append(queryList, q)
		}
	}

	startTime := time.Now()
	items, summaries, err := ecommerce.RunBijakBeli(ecommerce.BijakBeliOptions{
		Queries:      queryList,
		LimitPerItem: *limitPerItem,
		OutputPath:   *outputPath,
	})
	if err != nil {
		fmt.Printf("%s❌ [FAILED]%s Bijak-Beli ingestion error: %v\n", colorRed, colorReset, err)
		return
	}

	fmt.Printf("\n%s📊 [BIJAK-BELI SUMMARY] Price Diffusion & Store Comparison:%s\n", colorBold, colorReset)
	fmt.Printf("%-12s %-16s %-16s %-16s %-16s %s\n", "CATEGORY", "ALFAMART MIN", "ALFAMART AVG", "INDOMARET MIN", "INDOMARET AVG", "CHEAPEST")
	fmt.Println(strings.Repeat("─", 88))

	for _, s := range summaries {
		alfaMinStr := fmt.Sprintf("Rp %s", core.FormatIDR(s.AlfaMinPrice))
		if s.AlfaMinPrice == 0 {
			alfaMinStr = "N/A"
		}
		alfaAvgStr := fmt.Sprintf("Rp %s", core.FormatIDR(int(s.AlfaAvgPrice)))
		if s.AlfaAvgPrice == 0 {
			alfaAvgStr = "N/A"
		}
		indoMinStr := fmt.Sprintf("Rp %s", core.FormatIDR(s.IndoMinPrice))
		if s.IndoMinPrice == 0 {
			indoMinStr = "N/A"
		}
		indoAvgStr := fmt.Sprintf("Rp %s", core.FormatIDR(int(s.IndoAvgPrice)))
		if s.IndoAvgPrice == 0 {
			indoAvgStr = "N/A"
		}

		cheapestColor := colorGreen
		if s.CheapestStore == "alfamart" {
			cheapestColor = colorYellow
		} else if s.CheapestStore == "indomaret" {
			cheapestColor = colorCyan
		}

		fmt.Printf("%s%-12s%s %-16s %-16s %-16s %-16s %s%-14s%s\n",
			colorBold, s.Category, colorReset,
			alfaMinStr, alfaAvgStr,
			indoMinStr, indoAvgStr,
			cheapestColor, strings.ToUpper(s.CheapestStore), colorReset,
		)
	}

	fmt.Println(strings.Repeat("─", 88))
	csvPath := strings.TrimSuffix(*outputPath, ".json") + ".csv"
	_ = export.JSONToCSV(*outputPath, csvPath)
	fmt.Printf("%s✅ Ingested %d items across %d staples in %v%s\n",
		colorGreen, len(items), len(summaries), time.Since(startTime), colorReset)
	fmt.Printf("   JSON: %s\n   CSV:  %s\n\n", *outputPath, csvPath)
}

func handleBestBank(args []string) {
	printBanner()
	fs := flag.NewFlagSet("best-bank", flag.ExitOnError)
	profile := fs.String("profile", "micro", "Retailer operational profile: micro (Rp 25M), sme (Rp 120M), corporate (Rp 500M)")
	balance := fs.Float64("balance", 0, "Custom average idle balance in IDR")
	outputPath := fs.String("output", "data/banking/rates/latest.json", "Output dataset path")
	_ = fs.Parse(args)

	fmt.Printf("%s🏦 [RETAILER BANKING ADVISOR]%s Evaluating best Indonesian banks for retailers...\n", colorGreen, colorReset)
	fmt.Printf("   Operational Profile: %s%s%s", colorBold, strings.ToUpper(*profile), colorReset)
	if *balance > 0 {
		fmt.Printf(" | Custom Balance: Rp %s", core.FormatIDR(int(*balance)))
	}
	fmt.Println()
	fmt.Println()

	dataset, err := banking.RunBankingRatesIngestion(banking.BankingOptions{
		OutputPath:  *outputPath,
		ProfileType: *profile,
		IdleBalance: *balance,
	})
	if err != nil {
		fmt.Printf("%s❌ Error running banking analysis:%s %v\n", colorRed, colorReset, err)
		return
	}

	fmt.Printf("%s📊 Macro Benchmarks:%s BI-Rate: %.2f%% | LPS Guaranteed Deposit Rate: %.2f%% (Max: Rp 2.000.000.000)\n",
		colorBold, colorReset, dataset.MacroBenchmarks.BIRatePA, dataset.MacroBenchmarks.LPSGuaranteedRateIDR)
	fmt.Println(strings.Repeat("─", 112))

	fmt.Printf("%-5s %-26s %-16s %-11s %-15s %-15s %-10s %s\n",
		"RANK", "BANK NAME", "CATEGORY", "NET APY", "NET RETURN/YR", "ADMIN+FEE/YR", "USABILITY", "COMPOSITE")
	fmt.Println(strings.Repeat("─", 112))

	for _, res := range dataset.Evaluations {
		color := colorReset
		if res.Rank == 1 {
			color = colorGreen + colorBold
		} else if res.Rank <= 3 {
			color = colorYellow
		}

		netReturnStr := fmt.Sprintf("Rp %s", core.FormatIDR(int(res.NetAnnualBenefit)))
		if res.NetAnnualBenefit < 0 {
			netReturnStr = fmt.Sprintf("-Rp %s", core.FormatIDR(int(-res.NetAnnualBenefit)))
		}
		adminCostStr := fmt.Sprintf("Rp %s", core.FormatIDR(int(res.AnnualMaintenanceCost+res.AnnualTransferCost)))

		fmt.Printf("%s%-5d %-26s %-16s %-10.2f%% %-15s %-15s %-10d %.1f%s\n",
			color, res.Rank, res.BankName, res.BankType, res.EffectiveNetAPY, netReturnStr, adminCostStr, res.UsabilityIndex, res.CompositeScore, colorReset)
	}

	fmt.Println(strings.Repeat("─", 112))
	fmt.Printf("\n%s💡 Executive Retailer Takeaways:%s\n", colorBold, colorReset)
	for i := 0; i < 4 && i < len(dataset.Evaluations); i++ {
		r := dataset.Evaluations[i]
		fmt.Printf(" %s#%d %s (%s):%s %s\n", colorGreen, r.Rank, r.BankName, r.AccountName, colorReset, r.RecommendationSummary)
	}
	fmt.Printf("\nSaved full dataset to %s\n\n", *outputPath)
}

func handleStatus() {
	printBanner()
	fmt.Println("📊 IndoScraping Storage & Dataset Status:")
	fmt.Println(strings.Repeat("─", 85))

	dataDir := "data"
	if _, err := os.Stat(dataDir); os.IsNotExist(err) {
		fmt.Printf("%sNo data directory found yet. Run scrapers first.%s\n\n", colorYellow, colorReset)
		return
	}

	var totalFiles int
	var totalBytes int64

	_ = filepath.Walk(dataDir, func(path string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() && (strings.HasSuffix(path, ".json") || strings.HasSuffix(path, ".csv")) {
			totalFiles++
			totalBytes += info.Size()
			fmt.Printf(" • %-58s %8.2f KB   (%s)\n",
				path,
				float64(info.Size())/1024.0,
				info.ModTime().Format("2006-01-02 15:04:05"),
			)
		}
		return nil
	})

	fmt.Println(strings.Repeat("─", 85))
	fmt.Printf("Total Datasets: %d files | Total Size: %.2f KB\n\n", totalFiles, float64(totalBytes)/1024.0)
}

func handleRun(args []string) {
	if len(args) == 0 {
		fmt.Printf("%sError: scraper name required. Use 'indoscraping list' to view available scrapers.%s\n", colorRed, colorReset)
		return
	}

	scraperKey := args[0]
	fs := flag.NewFlagSet("run "+scraperKey, flag.ExitOnError)

	limitArticles := fs.Int("limit-articles", 5, "Number of articles to scrape")
	limitProducts := fs.Int("limit-products", 5, "Number of products to scrape")
	limitPages := fs.Int("limit-pages", 1, "Number of pages to scrape")
	limitItems := fs.Int("limit-items", 5, "Default item limit when running 'all'")
	query := fs.String("query", "susu", "Search query for e-commerce scrapers")
	area := fs.String("area", "jakarta/jakarta-barat/palmerah", "Target area for SewaKost")
	date := fs.String("date", "", "Target date for news crawlers")
	output := fs.String("output", "", "Custom output path")
	profile := fs.String("profile", "micro", "Retailer operational profile: micro, sme, or corporate")
	balance := fs.Float64("balance", 0, "Custom average idle balance in IDR")

	_ = fs.Parse(args[1:])

	if scraperKey == "all" {
		handleRunAll(*limitItems, *query, *area)
		return
	}

	startTime := time.Now()
	fmt.Printf("\n%s⚡ [START]%s Running scraper %s'%s'%s...\n", colorGreen, colorReset, colorBold, scraperKey, colorReset)

	switch scraperKey {
	case "detik":
		articles, err := news.ScrapeDetik(news.DetikOptions{
			Date:            *date,
			LimitCategories: 2,
			LimitArticles:   *limitArticles,
			OutputPath:      *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s Detik scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d Detik articles in %v\n", colorGreen, colorReset, len(articles), time.Since(startTime))
		for i, a := range articles {
			fmt.Printf("  %d. [%s] %s\n     🔗 %s\n", i+1, a.Category, a.Title, a.URL)
		}

	case "cnbc":
		articles, err := news.ScrapeCNBC(news.CNBCOptions{
			Date:          *date,
			LimitArticles: *limitArticles,
			OutputPath:    *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s CNBC scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d CNBC articles in %v\n", colorGreen, colorReset, len(articles), time.Since(startTime))
		for i, a := range articles {
			fmt.Printf("  %d. [%s] %s\n     🔗 %s\n", i+1, a.Category, a.Title, a.URL)
		}

	case "cnn":
		articles, err := news.ScrapeCNN(news.CNNOptions{
			Date:          *date,
			LimitArticles: *limitArticles,
			OutputPath:    *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s CNN scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d CNN articles in %v\n", colorGreen, colorReset, len(articles), time.Since(startTime))
		for i, a := range articles {
			fmt.Printf("  %d. [%s] %s\n     🔗 %s\n", i+1, a.Category, a.Title, a.URL)
		}

	case "kompas":
		articles, err := news.ScrapeKompas(news.KompasOptions{
			Date:          *date,
			LimitArticles: *limitArticles,
			OutputPath:    *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s Kompas scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d Kompas articles in %v\n", colorGreen, colorReset, len(articles), time.Since(startTime))
		for i, a := range articles {
			fmt.Printf("  %d. [%s] %s\n     🔗 %s\n", i+1, a.Category, a.Title, a.URL)
		}

	case "alfagift":
		products, err := ecommerce.ScrapeAlfagift(ecommerce.AlfagiftOptions{
			Query:         *query,
			LimitProducts: *limitProducts,
			OutputPath:    *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s Alfagift scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d Alfagift products for '%s' in %v\n", colorGreen, colorReset, len(products), *query, time.Since(startTime))
		for i, p := range products {
			fmt.Printf("  %d. %s (%s) - %s\n     🔗 %s\n", i+1, p.ProductName, p.PriceRaw, p.Seller, p.ProductURL)
		}

	case "blibli":
		products, err := ecommerce.ScrapeBlibli(ecommerce.BlibliOptions{
			Query:         *query,
			LimitProducts: *limitProducts,
			OutputPath:    *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s Blibli scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d Blibli products for '%s' in %v\n", colorGreen, colorReset, len(products), *query, time.Since(startTime))
		for i, p := range products {
			fmt.Printf("  %d. %s (%s) - %s\n     🔗 %s\n", i+1, p.ProductName, p.PriceRaw, p.Seller, p.ProductURL)
		}

	case "tokopedia":
		products, err := ecommerce.ScrapeTokopedia(ecommerce.TokopediaOptions{
			Query:         *query,
			LimitProducts: *limitProducts,
			OutputPath:    *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s Tokopedia scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d Tokopedia products for '%s' in %v\n", colorGreen, colorReset, len(products), *query, time.Since(startTime))
		for i, p := range products {
			fmt.Printf("  %d. %s (%s) - %s\n     🔗 %s\n", i+1, p.ProductName, p.PriceRaw, p.Seller, p.ProductURL)
		}

	case "indomaret":
		products, err := ecommerce.ScrapeIndomaret(ecommerce.IndomaretOptions{
			Query:         *query,
			LimitProducts: *limitProducts,
			OutputPath:    *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s Indomaret scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d Indomaret products for '%s' in %v\n", colorGreen, colorReset, len(products), *query, time.Since(startTime))
		for i, p := range products {
			fmt.Printf("  %d. %s (%s) - %s\n     🔗 %s\n", i+1, p.ProductName, p.PriceRaw, p.Seller, p.ProductURL)
		}

	case "jendela360":
		listings, err := property.ScrapeJendela360(property.Jendela360Options{
			LimitPages: *limitPages,
			OutputPath: *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s Jendela360 scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d Jendela360 listings in %v\n", colorGreen, colorReset, len(listings), time.Since(startTime))
		for i, item := range listings {
			fmt.Printf("  %d. [%s] %s (%s) - %s (Tower %s)\n     🔗 %s\n", i+1, item.Code, item.Name, item.PriceRaw, item.ApartmentName, item.Tower, item.URL)
		}

	case "sewakost":
		listings, err := property.ScrapeSewaKost(property.SewaKostOptions{
			Area:       *area,
			MaxPages:   *limitPages,
			OutputPath: *output,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s SewaKost scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d SewaKost listings in %v\n", colorGreen, colorReset, len(listings), time.Since(startTime))
		for i, item := range listings {
			fmt.Printf("  %d. [%s] %s (%s) - %s\n     🔗 %s\n", i+1, item.Type, item.Title, item.PriceRaw, item.Area, item.URL)
		}

	case "passmark":
		out := *output
		if out == "" {
			out = "data/benchmarks/passmark/latest.json"
		}
		items, err := hardware.ScrapePassMark(hardware.PassMarkOptions{
			OutputPath: out,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s PassMark scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Fetched %d PassMark benchmark ratings in %v\n", colorGreen, colorReset, len(items), time.Since(startTime))
		sampleCount := 10
		if len(items) < sampleCount {
			sampleCount = len(items)
		}
		for i := 0; i < sampleCount; i++ {
			item := items[i]
			fmt.Printf("  %d. [%s / %s] %s (Score: %d) - %s\n", i+1, item.Category, item.Segment, item.Name, item.Score, item.Benchmark)
		}
		if len(items) > sampleCount {
			fmt.Printf("  ... and %d more benchmark ratings saved to %s\n", len(items)-sampleCount, out)
		}

	case "banking", "rates":
		out := *output
		if out == "" {
			out = "data/banking/rates/latest.json"
		}
		dataset, err := banking.RunBankingRatesIngestion(banking.BankingOptions{
			OutputPath:  out,
			ProfileType: *profile,
			IdleBalance: *balance,
		})
		if err != nil {
			fmt.Printf("%s❌ [FAILED]%s Banking scraper error: %v\n", colorRed, colorReset, err)
			return
		}
		fmt.Printf("%s✅ [SUCCESS]%s Evaluated %d banks across commercial & digital segments in %v\n", colorGreen, colorReset, len(dataset.Banks), time.Since(startTime))
		for _, b := range dataset.Banks {
			fmt.Printf("  • [%s] %s (%s) - Monthly Admin: Rp %s | QRIS: %s\n",
				b.BankID, b.BankName, b.BankType, core.FormatIDR(int(b.MonthlyAdminFee)), b.QRISSettlementSpeed)
		}
		fmt.Printf("\nSaved dataset to %s. Run './bin/indoscraping best-bank' to view quantitative rankings.\n", out)

	default:
		fmt.Printf("%s❌ Unknown scraper key '%s'. Run 'indoscraping list' to view available keys.%s\n", colorRed, scraperKey, colorReset)
	}
}

type jobResult struct {
	key      string
	name     string
	count    int
	duration time.Duration
	err      error
}

func handleRunAll(limitItems int, query string, area string) {
	printBanner()
	fmt.Printf("%s🚀 [CONCURRENCY RUNNER]%s Executing all scrapers with managed goroutine pool (concurrency: 3)...\n", colorGreen, colorReset)
	fmt.Println(strings.Repeat("─", 80))

	startTime := time.Now()
	var wg sync.WaitGroup
	resultsChan := make(chan jobResult, 10)
	sem := make(chan struct{}, 3) // limit to 3 simultaneous network scrapers

	type scraperJob struct {
		name string
		run  func() (int, error)
	}

	jobs := []scraperJob{
		{
			name: "Detik News",
			run: func() (int, error) {
				res, err := news.ScrapeDetik(news.DetikOptions{LimitArticles: limitItems, LimitCategories: 2})
				return len(res), err
			},
		},
		{
			name: "CNBC Indonesia",
			run: func() (int, error) {
				res, err := news.ScrapeCNBC(news.CNBCOptions{LimitArticles: limitItems})
				return len(res), err
			},
		},
		{
			name: "CNN Indonesia",
			run: func() (int, error) {
				res, err := news.ScrapeCNN(news.CNNOptions{LimitArticles: limitItems})
				return len(res), err
			},
		},
		{
			name: "Kompas.com",
			run: func() (int, error) {
				res, err := news.ScrapeKompas(news.KompasOptions{LimitArticles: limitItems})
				return len(res), err
			},
		},
		{
			name: "Alfagift API",
			run: func() (int, error) {
				res, err := ecommerce.ScrapeAlfagift(ecommerce.AlfagiftOptions{Query: query, LimitProducts: limitItems})
				return len(res), err
			},
		},
		{
			name: "Blibli Gateway",
			run: func() (int, error) {
				res, err := ecommerce.ScrapeBlibli(ecommerce.BlibliOptions{Query: query, LimitProducts: limitItems})
				return len(res), err
			},
		},
		{
			name: "Tokopedia Marketplace",
			run: func() (int, error) {
				res, err := ecommerce.ScrapeTokopedia(ecommerce.TokopediaOptions{Query: query, LimitProducts: limitItems})
				return len(res), err
			},
		},
		{
			name: "Klik Indomaret API",
			run: func() (int, error) {
				res, err := ecommerce.ScrapeIndomaret(ecommerce.IndomaretOptions{Query: query, LimitProducts: limitItems})
				return len(res), err
			},
		},
		{
			name: "Jendela360 Property",
			run: func() (int, error) {
				res, err := property.ScrapeJendela360(property.Jendela360Options{LimitPages: 1})
				return len(res), err
			},
		},
		{
			name: "SewaKost Directory",
			run: func() (int, error) {
				res, err := property.ScrapeSewaKost(property.SewaKostOptions{Area: area, MaxPages: 1})
				return len(res), err
			},
		},
	}

	for _, j := range jobs {
		wg.Add(1)
		sem <- struct{}{}
		go func(job scraperJob) {
			defer func() {
				<-sem
				wg.Done()
			}()
			t0 := time.Now()
			// Run with 1 retry on network reset
			count, err := job.run()
			if err != nil {
				time.Sleep(300 * time.Millisecond)
				count, err = job.run()
			}
			resultsChan <- jobResult{name: job.name, count: count, duration: time.Since(t0), err: err}
		}(j)
	}

	wg.Wait()
	close(resultsChan)

	var totalItems int
	var successCount int
	var failCount int

	fmt.Printf("\n%-22s %-12s %-12s %s\n", "SCRAPER", "STATUS", "ITEMS", "DURATION")
	fmt.Println(strings.Repeat("─", 80))

	for res := range resultsChan {
		if res.err != nil {
			failCount++
			fmt.Printf("%-22s %s%-12s%s %-12d %v (Error: %v)\n", res.name, colorRed, "FAILED", colorReset, 0, res.duration, res.err)
		} else {
			successCount++
			totalItems += res.count
			fmt.Printf("%-22s %s%-12s%s %-12d %v\n", res.name, colorGreen, "SUCCESS", colorReset, res.count, res.duration)
		}
	}

	fmt.Println(strings.Repeat("─", 80))
	fmt.Printf("%s✨ Finished in %v | %d Succeeded, %d Failed | Total Items: %d%s\n\n",
		colorBold, time.Since(startTime), successCount, failCount, totalItems, colorReset)
}
