package cmd

import (
	"fmt"
	"os"

	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
)

var spaceCmd = &cobra.Command{
	Use:   "space",
	Short: "Manage MM-Wiki spaces",
	Long:  `Space management commands for listing, creating, updating and deleting spaces.`,
}

var spaceListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all spaces",
	RunE:  runSpaceList,
}

var spaceGetCmd = &cobra.Command{
	Use:   "get",
	Short: "Get space by ID",
	RunE:  runSpaceGet,
}

var spaceCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a new space",
	RunE:  runSpaceCreate,
}

var spaceUpdateCmd = &cobra.Command{
	Use:   "update",
	Short: "Update space information",
	RunE:  runSpaceUpdate,
}

var spaceDeleteCmd = &cobra.Command{
	Use:   "delete",
	Short: "Delete a space",
	RunE:  runSpaceDelete,
}

func init() {
	rootCmd.AddCommand(spaceCmd)
	spaceCmd.AddCommand(spaceListCmd)
	spaceCmd.AddCommand(spaceGetCmd)
	spaceCmd.AddCommand(spaceCreateCmd)
	spaceCmd.AddCommand(spaceUpdateCmd)
	spaceCmd.AddCommand(spaceDeleteCmd)

	// List flags
	spaceListCmd.Flags().Int("limit", 100, "Limit number of results")
	spaceListCmd.Flags().Int("offset", 0, "Offset for pagination")

	// Get flags
	spaceGetCmd.Flags().String("id", "", "Space ID (required)")
	spaceGetCmd.MarkFlagRequired("id")

	// Create flags
	spaceCreateCmd.Flags().String("name", "", "Space name (required)")
	spaceCreateCmd.Flags().String("description", "", "Space description")
	spaceCreateCmd.Flags().String("tags", "", "Space tags (comma separated)")
	spaceCreateCmd.Flags().String("level", "public", "Visit level (public/private)")
	spaceCreateCmd.Flags().Int("owner", 0, "Owner user ID (required)")
	spaceCreateCmd.MarkFlagRequired("name")
	spaceCreateCmd.MarkFlagRequired("owner")

	// Update flags
	spaceUpdateCmd.Flags().String("id", "", "Space ID (required)")
	spaceUpdateCmd.Flags().String("name", "", "Space name")
	spaceUpdateCmd.Flags().String("description", "", "Space description")
	spaceUpdateCmd.Flags().String("tags", "", "Space tags")
	spaceUpdateCmd.Flags().String("level", "", "Visit level (public/private)")
	spaceUpdateCmd.MarkFlagRequired("id")

	// Delete flags
	spaceDeleteCmd.Flags().String("id", "", "Space ID (required)")
	spaceDeleteCmd.MarkFlagRequired("id")
}

func runSpaceList(cmd *cobra.Command, args []string) error {
	limit, _ := cmd.Flags().GetInt("limit")
	offset, _ := cmd.Flags().GetInt("offset")

	spaces, err := cli.ListSpaces(limit, offset)
	if err != nil {
		return err
	}

	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader([]string{"ID", "Name", "Description", "Tags", "Level", "Owner"})
	table.SetAutoWrapText(false)

	for _, space := range spaces {
		table.Append([]string{
			space.SpaceID,
			space.Name,
			truncate(space.Description, 30),
			space.Tags,
			space.VisitLevel,
			space.UserID,
		})
	}

	table.Render()
	fmt.Printf("\nTotal: %d spaces\n", len(spaces))
	return nil
}

func runSpaceGet(cmd *cobra.Command, args []string) error {
	spaceID, _ := cmd.Flags().GetString("id")

	space, err := cli.GetSpace(spaceID)
	if err != nil {
		return err
	}

	fmt.Printf("Space Information:\n")
	fmt.Printf("  ID:           %s\n", space.SpaceID)
	fmt.Printf("  Name:         %s\n", space.Name)
	fmt.Printf("  Description:  %s\n", space.Description)
	fmt.Printf("  Tags:         %s\n", space.Tags)
	fmt.Printf("  Visit Level:  %s\n", space.VisitLevel)
	fmt.Printf("  Owner ID:     %s\n", space.UserID)
	fmt.Printf("  Share:        %s\n", getYesNo(space.IsShare))
	fmt.Printf("  Download:     %s\n", getYesNo(space.IsDownload))
	fmt.Printf("  Created:      %s\n", formatTimestamp(space.CreateTime))
	return nil
}

func runSpaceCreate(cmd *cobra.Command, args []string) error {
	name, _ := cmd.Flags().GetString("name")
	description, _ := cmd.Flags().GetString("description")
	tags, _ := cmd.Flags().GetString("tags")
	level, _ := cmd.Flags().GetString("level")
	ownerID, _ := cmd.Flags().GetInt("owner")

	if err := cli.CreateSpace(name, description, tags, level, ownerID); err != nil {
		return err
	}

	fmt.Printf("✓ Space '%s' created successfully.\n", name)
	return nil
}

func runSpaceUpdate(cmd *cobra.Command, args []string) error {
	spaceID, _ := cmd.Flags().GetString("id")
	name, _ := cmd.Flags().GetString("name")
	description, _ := cmd.Flags().GetString("description")
	tags, _ := cmd.Flags().GetString("tags")
	level, _ := cmd.Flags().GetString("level")

	// Get current space info
	currentSpace, err := cli.GetSpace(spaceID)
	if err != nil {
		return err
	}

	// Use current values if not provided
	if name == "" {
		name = currentSpace.Name
	}
	if !cmd.Flags().Changed("description") {
		description = currentSpace.Description
	}
	if !cmd.Flags().Changed("tags") {
		tags = currentSpace.Tags
	}
	if level == "" {
		level = currentSpace.VisitLevel
	}

	if err := cli.UpdateSpace(spaceID, name, description, tags, level); err != nil {
		return err
	}

	fmt.Printf("✓ Space %s updated successfully.\n", spaceID)
	return nil
}

func runSpaceDelete(cmd *cobra.Command, args []string) error {
	spaceID, _ := cmd.Flags().GetString("id")

	if err := cli.DeleteSpace(spaceID); err != nil {
		return err
	}

	fmt.Printf("✓ Space %s deleted successfully.\n", spaceID)
	return nil
}

func getYesNo(value string) string {
	if value == "1" {
		return "Yes"
	}
	return "No"
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}
