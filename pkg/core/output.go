package core

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// MetaSidecarPath returns the path for the sidecar metadata JSON file.
func MetaSidecarPath(outputPath string) string {
	if strings.HasSuffix(outputPath, ".json") {
		return strings.TrimSuffix(outputPath, ".json") + ".meta.json"
	}
	return outputPath + ".meta.json"
}

// AtomicWriteJSON writes data to path with atomic rename.
func AtomicWriteJSON(path string, data interface{}) error {
	dir := filepath.Dir(path)
	if dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory %s: %w", dir, err)
		}
	}

	bytes, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal JSON: %w", err)
	}

	tmpFile := fmt.Sprintf("%s.tmp.%d", path, time.Now().UnixNano())
	if err := os.WriteFile(tmpFile, bytes, 0644); err != nil {
		return fmt.Errorf("failed to write tmp file %s: %w", tmpFile, err)
	}

	if err := os.Rename(tmpFile, path); err != nil {
		_ = os.Remove(tmpFile)
		return fmt.Errorf("failed to rename %s to %s: %w", tmpFile, path, err)
	}

	return nil
}

// WriteLatestAndHistory writes primary payload to latestPath and optional historyPath, with metadata sidecar.
func WriteLatestAndHistory(latestPath string, historyPath string, payload interface{}, meta map[string]interface{}) error {
	if err := AtomicWriteJSON(latestPath, payload); err != nil {
		return err
	}

	if historyPath != "" {
		if err := AtomicWriteJSON(historyPath, payload); err != nil {
			return err
		}
	}

	if meta != nil {
		metaPath := MetaSidecarPath(latestPath)
		if err := AtomicWriteJSON(metaPath, meta); err != nil {
			return err
		}
	}

	return nil
}

var (
	htmlTagRegex = regexp.MustCompile(`<[^>]+>`)
	spacesRegex  = regexp.MustCompile(`\s+`)
	digitsRegex  = regexp.MustCompile(`[^\d]`)
)

// CleanText normalizes whitespace and removes tags.
func CleanText(text string) string {
	cleaned := htmlTagRegex.ReplaceAllString(text, " ")
	cleaned = strings.ReplaceAll(cleaned, "\u00a0", " ")
	cleaned = strings.ReplaceAll(cleaned, "\n", " ")
	cleaned = strings.ReplaceAll(cleaned, "\r", " ")
	cleaned = strings.ReplaceAll(cleaned, "\t", " ")
	cleaned = spacesRegex.ReplaceAllString(cleaned, " ")
	return strings.TrimSpace(cleaned)
}

// ParseNumericPrice converts currency strings like "Rp 15.000" or "Rp15.000,00" into integer 15000.
func ParseNumericPrice(raw string) int {
	digits := digitsRegex.ReplaceAllString(raw, "")
	if digits == "" {
		return 0
	}
	val, err := strconv.Atoi(digits)
	if err != nil {
		return 0
	}
	return val
}

// FormatIDR formats an integer to Indonesian Rupiah thousands dot format (e.g. 2630000 -> "2.630.000").
func FormatIDR(n int) string {
	in := strconv.Itoa(n)
	var out []byte
	l := len(in)
	for i, c := range in {
		if i > 0 && (l-i)%3 == 0 {
			out = append(out, '.')
		}
		out = append(out, byte(c))
	}
	return string(out)
}

