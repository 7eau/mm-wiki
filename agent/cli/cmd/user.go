package cmd

import (
	"fmt"
	"os"

	"github.com/olekukonko/tablewriter"
	"github.com/phachon/mm-wiki/agent/cli/client"
	"github.com/spf13/cobra"
)

var userCmd = &cobra.Command{
	Use:   "user",
	Short: "Manage MM-Wiki users",
	Long:  `User management commands for listing, creating, updating and deleting users.`,
}

var userListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all users",
	RunE:  runUserList,
}

var userGetCmd = &cobra.Command{
	Use:   "get",
	Short: "Get user by ID",
	RunE:  runUserGet,
}

var userCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a new user",
	RunE:  runUserCreate,
}

var userUpdateCmd = &cobra.Command{
	Use:   "update",
	Short: "Update user information",
	RunE:  runUserUpdate,
}

var userDeleteCmd = &cobra.Command{
	Use:   "delete",
	Short: "Delete a user",
	RunE:  runUserDelete,
}

func init() {
	rootCmd.AddCommand(userCmd)
	userCmd.AddCommand(userListCmd)
	userCmd.AddCommand(userGetCmd)
	userCmd.AddCommand(userCreateCmd)
	userCmd.AddCommand(userUpdateCmd)
	userCmd.AddCommand(userDeleteCmd)

	// List flags
	userListCmd.Flags().Int("limit", 100, "Limit number of results")
	userListCmd.Flags().Int("offset", 0, "Offset for pagination")
	userListCmd.Flags().String("search", "", "Search keyword")

	// Get flags
	userGetCmd.Flags().String("id", "", "User ID (required)")
	userGetCmd.MarkFlagRequired("id")

	// Create flags
	userCreateCmd.Flags().String("username", "", "Username (required)")
	userCreateCmd.Flags().String("password", "", "Password (required)")
	userCreateCmd.Flags().String("name", "", "Display name")
	userCreateCmd.Flags().String("email", "", "Email address")
	userCreateCmd.Flags().String("phone", "", "Phone number")
	userCreateCmd.Flags().Int("role", 3, "Role ID (1=super admin, 2=admin, 3=user)")
	userCreateCmd.MarkFlagRequired("username")
	userCreateCmd.MarkFlagRequired("password")

	// Update flags
	userUpdateCmd.Flags().String("id", "", "User ID (required)")
	userUpdateCmd.Flags().String("name", "", "Display name")
	userUpdateCmd.Flags().String("email", "", "Email address")
	userUpdateCmd.Flags().String("phone", "", "Phone number")
	userUpdateCmd.Flags().Int("role", 0, "Role ID")
	userUpdateCmd.MarkFlagRequired("id")

	// Delete flags
	userDeleteCmd.Flags().String("id", "", "User ID (required)")
	userDeleteCmd.MarkFlagRequired("id")
}

func runUserList(cmd *cobra.Command, args []string) error {
	limit, _ := cmd.Flags().GetInt("limit")
	offset, _ := cmd.Flags().GetInt("offset")
	search, _ := cmd.Flags().GetString("search")

	users, err := cli.ListUsers(search, limit, offset)
	if err != nil {
		return err
	}

	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader([]string{"ID", "Username", "Name", "Email", "Role", "Status"})
	table.SetAutoWrapText(false)

	for _, user := range users {
		roleName := getRoleName(user.RoleID)
		status := "Active"
		if user.IsForbidden == "1" {
			status = "Forbidden"
		}
		table.Append([]string{
			user.UserID,
			user.Username,
			user.Name,
			user.Email,
			roleName,
			status,
		})
	}

	table.Render()
	fmt.Printf("\nTotal: %d users\n", len(users))
	return nil
}

func runUserGet(cmd *cobra.Command, args []string) error {
	userID, _ := cmd.Flags().GetString("id")

	user, err := cli.GetUser(userID)
	if err != nil {
		return err
	}

	fmt.Printf("User Information:\n")
	fmt.Printf("  ID:          %s\n", user.UserID)
	fmt.Printf("  Username:    %s\n", user.Username)
	fmt.Printf("  Name:        %s\n", user.Name)
	fmt.Printf("  Email:       %s\n", user.Email)
	fmt.Printf("  Phone:       %s\n", user.Phone)
	fmt.Printf("  Role:        %s (%s)\n", getRoleName(user.RoleID), user.RoleID)
	fmt.Printf("  Status:      %s\n", getUserStatus(user.IsForbidden))
	fmt.Printf("  Created:     %s\n", formatTimestamp(user.CreateTime))
	fmt.Printf("  Last Login:  %s\n", formatTimestamp(user.LastTime))
	return nil
}

func runUserCreate(cmd *cobra.Command, args []string) error {
	username, _ := cmd.Flags().GetString("username")
	password, _ := cmd.Flags().GetString("password")
	name, _ := cmd.Flags().GetString("name")
	email, _ := cmd.Flags().GetString("email")
	phone, _ := cmd.Flags().GetString("phone")
	roleID, _ := cmd.Flags().GetInt("role")

	if err := cli.CreateUser(username, password, name, email, phone, roleID); err != nil {
		return err
	}

	fmt.Printf("✓ User '%s' created successfully.\n", username)
	return nil
}

func runUserUpdate(cmd *cobra.Command, args []string) error {
	userID, _ := cmd.Flags().GetString("id")
	name, _ := cmd.Flags().GetString("name")
	email, _ := cmd.Flags().GetString("email")
	phone, _ := cmd.Flags().GetString("phone")
	roleID, _ := cmd.Flags().GetInt("role")

	// Get current user info
	currentUser, err := cli.GetUser(userID)
	if err != nil {
		return err
	}

	// Use current values if not provided
	if name == "" {
		name = currentUser.Name
	}
	if email == "" {
		email = currentUser.Email
	}
	if phone == "" {
		phone = currentUser.Phone
	}
	if !cmd.Flags().Changed("role") {
		roleID = parseInt(currentUser.RoleID)
	}

	if err := cli.UpdateUser(userID, name, email, phone, roleID); err != nil {
		return err
	}

	fmt.Printf("✓ User %s updated successfully.\n", userID)
	return nil
}

func runUserDelete(cmd *cobra.Command, args []string) error {
	userID, _ := cmd.Flags().GetString("id")

	if err := cli.DeleteUser(userID); err != nil {
		return err
	}

	fmt.Printf("✓ User %s deleted successfully.\n", userID)
	return nil
}

func getRoleName(roleID string) string {
	switch roleID {
	case "1":
		return "Super Admin"
	case "2":
		return "Admin"
	case "3":
		return "User"
	default:
		return "Unknown"
	}
}

func getUserStatus(isForbidden string) string {
	if isForbidden == "1" {
		return "Forbidden"
	}
	return "Active"
}

func parseInt(s string) int {
	var i int
	fmt.Sscanf(s, "%d", &i)
	return i
}
