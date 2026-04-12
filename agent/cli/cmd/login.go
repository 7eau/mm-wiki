package cmd

import (
	"fmt"

	"github.com/phachon/mm-wiki/agent/cli/client"
	"github.com/spf13/cobra"
)

var loginCmd = &cobra.Command{
	Use:   "login",
	Short: "Login to MM-Wiki server",
	Long:  `Authenticate with MM-Wiki server and save session for subsequent commands.`,
	RunE:  runLogin,
}

var logoutCmd = &cobra.Command{
	Use:   "logout",
	Short: "Logout from MM-Wiki server",
	Long:  `Clear the saved session and logout from the server.`,
	RunE:  runLogout,
}

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Check login status",
	Long:  `Check if currently logged in and show session information.`,
	RunE:  runStatus,
}

func init() {
	rootCmd.AddCommand(loginCmd)
	rootCmd.AddCommand(logoutCmd)
	rootCmd.AddCommand(statusCmd)

	loginCmd.Flags().StringVar(&baseURL, "url", "", "MM-Wiki base URL (required)")
	loginCmd.Flags().StringVarP(&username, "username", "u", "", "Username (required)")
	loginCmd.Flags().StringVarP(&password, "password", "p", "", "Password (required)")
	loginCmd.MarkFlagRequired("url")
	loginCmd.MarkFlagRequired("username")
	loginCmd.MarkFlagRequired("password")
}

func runLogin(cmd *cobra.Command, args []string) error {
	// Create client
	var err error
	cli, err = client.NewClient(baseURL)
	if err != nil {
		return fmt.Errorf("failed to create client: %v", err)
	}

	fmt.Printf("Logging in to %s as %s...\n", baseURL, username)

	// Login
	if err := cli.Login(username, password); err != nil {
		return err
	}

	fmt.Printf("✓ Login successful! Welcome, %s.\n", username)
	fmt.Println("Session saved. You can now run other commands without --url, --username, --password flags.")
	
	return nil
}

func runLogout(cmd *cobra.Command, args []string) error {
	// Create client (will load saved session if exists)
	var err error
	cli, err = client.NewClient("")
	if err != nil {
		return fmt.Errorf("failed to create client: %v", err)
	}

	if !cli.IsLoggedIn() {
		fmt.Println("Not currently logged in.")
		return nil
	}

	// Logout from server
	if err := cli.Logout(); err != nil {
		return err
	}

	fmt.Println("✓ Logged out successfully.")
	return nil
}

func runStatus(cmd *cobra.Command, args []string) error {
	// Create client (will load saved session if exists)
	var err error
	cli, err = client.NewClient("")
	if err != nil {
		return fmt.Errorf("failed to create client: %v", err)
	}

	if cli.IsLoggedIn() {
		fmt.Printf("✓ Logged in as %s at %s\n", cli.GetUsername(), cli.GetBaseURL())
	} else {
		fmt.Println("✗ Not logged in.")
		fmt.Println("Run 'mmwiki-cli login --url <url> --username <user> --password <pass>' to login.")
	}

	return nil
}
