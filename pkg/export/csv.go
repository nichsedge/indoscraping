package export

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// JSONToCSV converts a JSON array of flat or nested objects into a standard CSV file.
func JSONToCSV(jsonPath string, csvPath string) error {
	bytes, err := os.ReadFile(jsonPath)
	if err != nil {
		return fmt.Errorf("failed to read JSON file %s: %w", jsonPath, err)
	}

	var rows []map[string]interface{}
	if err := json.Unmarshal(bytes, &rows); err != nil {
		return fmt.Errorf("failed to unmarshal JSON: %w", err)
	}

	if len(rows) == 0 {
		return fmt.Errorf("JSON file contains no rows")
	}

	if csvPath == "" {
		csvPath = strings.TrimSuffix(jsonPath, ".json") + ".csv"
	}

	dir := filepath.Dir(csvPath)
	if dir != "" {
		_ = os.MkdirAll(dir, 0755)
	}

	file, err := os.Create(csvPath)
	if err != nil {
		return fmt.Errorf("failed to create CSV file: %w", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Collect unique keys
	keySet := make(map[string]bool)
	for _, row := range rows {
		for k := range row {
			keySet[k] = true
		}
	}

	var headers []string
	for k := range keySet {
		headers = append(headers, k)
	}
	sort.Strings(headers)

	if err := writer.Write(headers); err != nil {
		return err
	}

	for _, row := range rows {
		var record []string
		for _, h := range headers {
			val := row[h]
			record = append(record, fmt.Sprintf("%v", val))
		}
		if err := writer.Write(record); err != nil {
			return err
		}
	}

	return nil
}

// ExportAllToCSV scans all latest.json files in dataDir and generates corresponding .csv files.
func ExportAllToCSV(dataDir string) ([]string, error) {
	var exported []string
	err := filepath.Walk(dataDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}
		if strings.HasSuffix(path, "latest.json") {
			csvPath := strings.TrimSuffix(path, ".json") + ".csv"
			if err := JSONToCSV(path, csvPath); err == nil {
				exported = append(exported, csvPath)
			}
		}
		return nil
	})
	return exported, err
}
