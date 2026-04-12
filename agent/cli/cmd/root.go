package cmd

import (
	"fmt"
	"os"

	"github.com/phachon/mm-wiki/agent/cli/client"
	"github.com/spf13/cobra"
)

var (
	// Global flags
	baseURL  string
	username string
	password string

	// Global client
	cli *client.MMWikiClient

	rootCmd = &cobra.Command{
		Use:   "mmwiki-cli",
		Short: "MM-Wiki CLI Tool - Manage your wiki from command line",
		Long: `MM-Wiki CLI Tool provides command-line interface for managing MM-Wiki via HTTP API.

This tool allows you to:
- Manage users, spaces, and documents
- View and edit wiki content
- Get system statistics

Examples:
  # Login to MM-Wiki server
  mmwiki-cli login --url http://wiki.example.com:8081 --username admin --password secret

  # List all users
  mmwiki-cli user list

  # Create a new space
  mmwiki-cli space create --name "MySpace" --description "A new space"

  # List documents in a space
  mmwiki-cli doc list --space 1

  # Read document content
  mmwiki-cli doc read --id 123

  # Write document content from file
  mmwiki-cli doc write --id 123 --file content.md`,
		PersistentPreRunE: initClient,
	}
)

func Execute() error {
	return rootCmd.Execute()
}

func init() {
	rootCmd.PersistentFlags().StringVar(&baseURL, "url", "", "MM-Wiki base URL (e.g., http://localhost:8081)")
	rootCmd.PersistentFlags().StringVarP(&username, "username", "u", "", "Username for authentication")
	rootCmd.PersistentFlags().StringVarP(&password, "password", "p", "", "Password for authentication")
}

func initClient(cmd *cobra.Command, args []string) error {
	// Skip for login and version commands
	if cmd.Name() == "login" || cmd.Name() == "version" || cmd.Name() == "help" {
		return nil
	}

	// Try to load from saved session first
	var err error
	cli, err = client.NewClient("")
	if err != nil {
		return fmt.Errorf("failed to create client: %v", err)
	}

	// Check if URL is provided or we have a saved session
	if baseURL != "" {
		cli, _ = client.NewClient(baseURL)
	}

	// Check if logged in
	if !cli.IsLoggedIn() {
		// Try to login with provided credentials
		if username != "" && password != "" {
			if err := cli.Login(username, password); err != nil {
				return fmt.Errorf("authentication failed: %v", err)
			}
		} else {
			fmt.Fprintln(os.Stderr, "Error: Not logged in. Please run 'mmwiki-cli login' first or provide --username and --password")
			os.Exit(1)
		}
	}

	return nil
}

// GetClient returns the global client instance
func GetClient() *client.MMWikiClient {
	return cli
}
