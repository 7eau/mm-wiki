package cmd

import (
	"strconv"
	"time"
)

// formatTimestamp converts a Unix timestamp string to human-readable format
func formatTimestamp(timestamp string) string {
	if timestamp == "" || timestamp == "0" {
		return "N/A"
	}

	// Try to parse as Unix timestamp
	ts, err := strconv.ParseInt(timestamp, 10, 64)
	if err != nil {
		return timestamp
	}

	t := time.Unix(ts, 0)
	return t.Format("2006-01-02 15:04:05")
}

