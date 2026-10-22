package browser

import (
	"context"
	"fmt"
	"os"
	"os/exec"

	"github.com/chromedp/chromedp"
)

// FindChromium looks for available chromium/chrome binary in known paths.
func FindChromium() (string, error) {
	if env := os.Getenv("CHROME_BIN"); env != "" {
		if _, err := os.Stat(env); err == nil {
			return env, nil
		}
	}
	if env := os.Getenv("CHROMIUM_PATH"); env != "" {
		if _, err := os.Stat(env); err == nil {
			return env, nil
		}
	}

	candidates := []string{
		"/data/data/com.termux/files/usr/bin/chromium-browser",
		"/data/data/com.termux/files/usr/bin/chromium",
		"chromium-browser",
		"chromium",
		"google-chrome",
		"google-chrome-stable",
	}

	for _, cand := range candidates {
		if path, err := exec.LookPath(cand); err == nil {
			return path, nil
		}
		if _, err := os.Stat(cand); err == nil {
			return cand, nil
		}
	}

	return "", fmt.Errorf("chromium browser binary not found in system or Termux path")
}

// NewExecAllocator creates a chromedp ExecAllocator configured for Android Termux & Linux containers.
func NewExecAllocator(parent context.Context, headless bool) (context.Context, context.CancelFunc, error) {
	binPath, err := FindChromium()
	if err != nil {
		return nil, nil, err
	}

	opts := append(chromedp.DefaultExecAllocatorOptions[:],
		chromedp.ExecPath(binPath),
		chromedp.NoSandbox,
		chromedp.DisableGPU,
		chromedp.Flag("disable-dev-shm-usage", true),
		chromedp.Flag("disable-software-rasterizer", true),
		chromedp.Flag("disable-blink-features", "AutomationControlled"),
		chromedp.Flag("enable-automation", false),
		chromedp.WindowSize(1920, 1080),
		chromedp.UserAgent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"),
	)

	if headless {
		opts = append(opts, chromedp.Headless)
	}

	allocCtx, cancel := chromedp.NewExecAllocator(parent, opts...)
	return allocCtx, cancel, nil
}
