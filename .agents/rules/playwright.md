---
trigger: always_on
---

-When using Playwright, launch the browser using the system-installed Chrome: `chromium.launch({ channel: 'chrome', headless: true })`.
- Ensure the configuration relies on existing binaries and skips any runtime downloads (e.g., by assuming PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 is set).