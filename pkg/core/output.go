package core

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"
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

// CleanText normalizes whitespace and removes HTML tags with a single-pass scanner.
func CleanText(text string) string {
	if text == "" {
		return ""
	}

	var sb strings.Builder
	sb.Grow(len(text))

	inTag := false
	prevSpace := true // Start true to automatically trim leading whitespace

	i := 0
	for i < len(text) {
		r, size := utf8.DecodeRuneInString(text[i:])
		i += size

		if inTag {
			if r == '>' {
				inTag = false
				if !prevSpace {
					sb.WriteByte(' ')
					prevSpace = true
				}
			}
			continue
		}

		if r == '<' {
			inTag = true
			continue
		}

		// Normalize all unicode & ASCII whitespace
		if r == ' ' || r == '\t' || r == '\n' || r == '\r' || r == '\u00a0' || unicode.IsSpace(r) {
			if !prevSpace {
				sb.WriteByte(' ')
				prevSpace = true
			}
			continue
		}

		sb.WriteRune(r)
		prevSpace = false
	}

	res := sb.String()
	if len(res) > 0 && res[len(res)-1] == ' ' {
		res = res[:len(res)-1]
	}
	return res
}

// ParseNumericPrice converts currency strings like "Rp 15.000", "Rp15.000,00", "Rp 1.250.000" into integer.
// Correctly handles Indonesian decimal comma (cents/sen) and avoids regex overhead.
func ParseNumericPrice(raw string) int {
	if raw == "" {
		return 0
	}

	// Look for comma which in Indonesian currency signifies decimals/sen (e.g. ",00")
	// If followed by digits at the end, truncate the decimal portion.
	clean := raw
	if commaIdx := strings.LastIndexByte(clean, ','); commaIdx != -1 {
		// If comma is followed by 1 or 2 digits at the end (cents), ignore the fractional part
		afterComma := strings.TrimRight(clean[commaIdx+1:], " \t\r\n-")
		if len(afterComma) <= 2 {
			isDigits := true
			for _, c := range afterComma {
				if c < '0' || c > '9' {
					isDigits = false
					break
				}
			}
			if isDigits {
				clean = clean[:commaIdx]
			}
		}
	}

	val := 0
	foundDigit := false
	for i := 0; i < len(clean); i++ {
		b := clean[i]
		if b >= '0' && b <= '9' {
			val = val*10 + int(b-'0')
			foundDigit = true
		}
	}

	if !foundDigit {
		return 0
	}
	return val
}

// FormatIDR formats an integer to Indonesian Rupiah thousands dot format (e.g. 2630000 -> "2.630.000").
// Uses stack-allocated byte buffer to avoid heap allocations.
func FormatIDR(n int) string {
	if n == 0 {
		return "0"
	}

	sign := false
	if n < 0 {
		sign = true
		n = -n
	}

	var buf [32]byte
	pos := len(buf)
	count := 0

	for n > 0 {
		if count > 0 && count%3 == 0 {
			pos--
			buf[pos] = '.'
		}
		pos--
		buf[pos] = byte('0' + (n % 10))
		count++
		n /= 10
	}

	if sign {
		pos--
		buf[pos] = '-'
	}

	return string(buf[pos:])
}

