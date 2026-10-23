package core

import (
	"net"
	"net/http"
	"time"
)

var (
	// DefaultTransport is an optimized HTTP transport with keep-alive connection pooling
	DefaultTransport = &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   15 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		ForceAttemptHTTP2:     true,
		MaxIdleConns:          100,
		MaxIdleConnsPerHost:   10,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
	}

	// DefaultClient is the shared HTTP client across scrapers with pooled connections and 30s timeout
	DefaultClient = &http.Client{
		Transport: DefaultTransport,
		Timeout:   30 * time.Second,
	}
)

// HTTPClient returns the shared HTTP client with keep-alive connection pooling.
func HTTPClient() *http.Client {
	return DefaultClient
}
