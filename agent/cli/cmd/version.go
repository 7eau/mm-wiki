package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

const version = "0.1.0"

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print version information",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("mmwiki-cli version %s\n", version)
		fmt.Println("MM-Wiki Command Line Interface Tool")
		fmt.Println("Repository: https://github.com/phachon/mm-wiki")
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}
