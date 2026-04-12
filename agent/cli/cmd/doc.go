package cmd

import (
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/olekukonko/tablewriter"
	"github.com/phachon/mm-wiki/agent/cli/client"
	"github.com/spf13/cobra"
)

var docCmd = &cobra.Command{
	Use:   "doc",
	Short: "Manage MM-Wiki documents",
	Long:  `Document management commands for listing, creating, reading, writing and deleting documents.`,
}

var docListCmd = &cobra.Command{
	Use:   "list",
	Short: "List documents in a space",
	RunE:  runDocList,
}

var docGetCmd = &cobra.Command{
	Use:   "get",
	Short: "Get document details",
	RunE:  runDocGet,
}

var docTreeCmd = &cobra.Command{
	Use:   "tree",
	Short: "Show document tree structure",
	RunE:  runDocTree,
}

var docCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a new document",
	RunE:  runDocCreate,
}

var docUpdateCmd = &cobra.Command{
	Use:   "update",
	Short: "Update document metadata",
	RunE:  runDocUpdate,
}

var docReadCmd = &cobra.Command{
	Use:   "read",
	Short: "Read document content",
	RunE:  runDocRead,
}

var docWriteCmd = &cobra.Command{
	Use:   "write",
	Short: "Write document content",
	RunE:  runDocWrite,
}

var docDeleteCmd = &cobra.Command{
	Use:   "delete",
	Short: "Delete a document",
	RunE:  runDocDelete,
}

var docMoveCmd = &cobra.Command{
	Use:   "move",
	Short: "Move document to another location",
	RunE:  runDocMove,
}

func init() {
	rootCmd.AddCommand(docCmd)
	docCmd.AddCommand(docListCmd)
	docCmd.AddCommand(docGetCmd)
	docCmd.AddCommand(docTreeCmd)
	docCmd.AddCommand(docCreateCmd)
	docCmd.AddCommand(docUpdateCmd)
	docCmd.AddCommand(docReadCmd)
	docCmd.AddCommand(docWriteCmd)
	docCmd.AddCommand(docDeleteCmd)
	docCmd.AddCommand(docMoveCmd)

	// List flags
	docListCmd.Flags().String("space", "", "Space ID (required)")
	docListCmd.Flags().String("parent", "0", "Parent document ID")
	docListCmd.MarkFlagRequired("space")

	// Get flags
	docGetCmd.Flags().String("id", "", "Document ID (required)")
	docGetCmd.MarkFlagRequired("id")

	// Tree flags
	docTreeCmd.Flags().String("space", "", "Space ID (required)")
	docTreeCmd.MarkFlagRequired("space")

	// Create flags
	docCreateCmd.Flags().String("space", "", "Space ID (required)")
	docCreateCmd.Flags().String("parent", "0", "Parent document ID")
	docCreateCmd.Flags().String("name", "", "Document name (required)")
	docCreateCmd.Flags().String("type", "page", "Document type (page/dir)")
	docCreateCmd.MarkFlagRequired("space")
	docCreateCmd.MarkFlagRequired("name")

	// Update flags
	docUpdateCmd.Flags().String("id", "", "Document ID (required)")
	docUpdateCmd.Flags().String("name", "", "New name (required)")
	docUpdateCmd.MarkFlagRequired("id")
	docUpdateCmd.MarkFlagRequired("name")

	// Read flags
	docReadCmd.Flags().String("id", "", "Document ID (required)")
	docReadCmd.Flags().String("output", "", "Output to file instead of stdout")
	docReadCmd.MarkFlagRequired("id")

	// Write flags
	docWriteCmd.Flags().String("id", "", "Document ID (required)")
	docWriteCmd.Flags().String("content", "", "Content to write (or use --file)")
	docWriteCmd.Flags().String("file", "", "Read content from file")
	docWriteCmd.Flags().String("comment", "Updated via CLI", "Edit comment")
	docWriteCmd.MarkFlagRequired("id")

	// Delete flags
	docDeleteCmd.Flags().String("id", "", "Document ID (required)")
	docDeleteCmd.MarkFlagRequired("id")

	// Move flags
	docMoveCmd.Flags().String("id", "", "Document ID to move (required)")
	docMoveCmd.Flags().String("target", "", "Target parent document ID (required)")
	docMoveCmd.Flags().String("type", "next", "Move type (inner/inner_next/next/prev)")
	docMoveCmd.MarkFlagRequired("id")
	docMoveCmd.MarkFlagRequired("target")
}

func runDocList(cmd *cobra.Command, args []string) error {
	spaceID, _ := cmd.Flags().GetString("space")
	parentID, _ := cmd.Flags().GetString("parent")

	docs, err := cli.ListDocuments(spaceID, parentID)
	if err != nil {
		return err
	}

	if len(docs) == 0 {
		fmt.Println("No documents found")
		return nil
	}

	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader([]string{"ID", "Name", "Type", "Seq", "Created"})

	for _, doc := range docs {
		docType := "Page"
		if doc.Type == "2" {
			docType = "Dir"
		}
		table.Append([]string{
			doc.DocumentID,
			doc.Name,
			docType,
			doc.Sequence,
			formatTimestamp(doc.CreateTime),
		})
	}

	table.Render()
	fmt.Printf("\nTotal: %d documents\n", len(docs))
	return nil
}

func runDocGet(cmd *cobra.Command, args []string) error {
	docID, _ := cmd.Flags().GetString("id")

	doc, err := cli.GetDocument(docID)
	if err != nil {
		return err
	}

	fmt.Printf("Document Information:\n")
	fmt.Printf("  ID:           %s\n", doc.DocumentID)
	fmt.Printf("  Name:         %s\n", doc.Name)
	fmt.Printf("  Space ID:     %s\n", doc.SpaceID)
	fmt.Printf("  Parent ID:    %s\n", doc.ParentID)
	fmt.Printf("  Type:         %s\n", getDocTypeName(doc.Type))
	fmt.Printf("  Path:         %s\n", doc.Path)
	fmt.Printf("  Sequence:     %s\n", doc.Sequence)
	fmt.Printf("  Created:      %s\n", formatTimestamp(doc.CreateTime))
	fmt.Printf("  Updated:      %s\n", formatTimestamp(doc.UpdateTime))
	return nil
}

func runDocTree(cmd *cobra.Command, args []string) error {
	spaceID, _ := cmd.Flags().GetString("space")

	// Get all documents in space
	docs, err := cli.ListDocuments(spaceID, "0")
	if err != nil {
		return err
	}

	// Build tree structure
	docMap := make(map[string][]map[string]string)
	for _, doc := range docs {
		parentID := doc.ParentID
		docMap[parentID] = append(docMap[parentID], map[string]string{
			"id":   doc.DocumentID,
			"name": doc.Name,
			"type": doc.Type,
		})
	}

	// Recursively fetch all documents
	allDocs, err := fetchAllDocs(cli, spaceID, docMap, "0")
	if err != nil {
		return err
	}

	// Print tree
	fmt.Printf("Document Tree (Space %s):\n", spaceID)
	printDocTree(allDocs, "0", 0)

	fmt.Printf("\nTotal: %d items\n", len(allDocs))
	return nil
}

func runDocCreate(cmd *cobra.Command, args []string) error {
	spaceID, _ := cmd.Flags().GetString("space")
	parentID, _ := cmd.Flags().GetString("parent")
	name, _ := cmd.Flags().GetString("name")
	docType, _ := cmd.Flags().GetString("type")

	docTypeVal := "1" // page
	if docType == "dir" || docType == "directory" {
		docTypeVal = "2"
	}

	doc, err := cli.CreateDocument(spaceID, parentID, name, docTypeVal, 0)
	if err != nil {
		return err
	}

	fmt.Printf("✓ Document '%s' created successfully.\n", name)
	fmt.Printf("  Space: %s, Parent: %s\n", doc.SpaceID, doc.ParentID)
	return nil
}

func runDocUpdate(cmd *cobra.Command, args []string) error {
	docID, _ := cmd.Flags().GetString("id")
	name, _ := cmd.Flags().GetString("name")

	if err := cli.UpdateDocument(docID, name, 0); err != nil {
		return err
	}

	fmt.Printf("✓ Document %s renamed to '%s'.\n", docID, name)
	return nil
}

func runDocRead(cmd *cobra.Command, args []string) error {
	docID, _ := cmd.Flags().GetString("id")
	outputFile, _ := cmd.Flags().GetString("output")

	doc, err := cli.GetDocumentDetail(docID)
	if err != nil {
		return err
	}

	if outputFile != "" {
		if err := os.WriteFile(outputFile, []byte(doc.Content), 0644); err != nil {
			return fmt.Errorf("failed to write file: %v", err)
		}
		fmt.Printf("✓ Content saved to %s\n", outputFile)
	} else {
		fmt.Print(doc.Content)
	}

	return nil
}

func runDocWrite(cmd *cobra.Command, args []string) error {
	docID, _ := cmd.Flags().GetString("id")
	contentInput, _ := cmd.Flags().GetString("content")
	filePath, _ := cmd.Flags().GetString("file")
	comment, _ := cmd.Flags().GetString("comment")

	// Get current document info
	doc, err := cli.GetDocumentDetail(docID)
	if err != nil {
		return err
	}

	// Get content
	var content string
	if filePath != "" {
		data, err := os.ReadFile(filePath)
		if err != nil {
			return fmt.Errorf("failed to read file: %v", err)
		}
		content = string(data)
	} else if contentInput != "" {
		content = contentInput
	} else {
		// Read from stdin
		data, err := io.ReadAll(os.Stdin)
		if err != nil {
			return fmt.Errorf("failed to read stdin: %v", err)
		}
		content = string(data)
	}

	if err := cli.SaveDocumentContent(docID, doc.Name, content, comment, 0); err != nil {
		return err
	}

	fmt.Printf("✓ Document %s updated successfully.\n", docID)
	return nil
}

func runDocDelete(cmd *cobra.Command, args []string) error {
	docID, _ := cmd.Flags().GetString("id")

	if err := cli.DeleteDocument(docID); err != nil {
		return err
	}

	fmt.Printf("✓ Document %s deleted successfully.\n", docID)
	return nil
}

func runDocMove(cmd *cobra.Command, args []string) error {
	docID, _ := cmd.Flags().GetString("id")
	targetID, _ := cmd.Flags().GetString("target")
	moveType, _ := cmd.Flags().GetString("type")

	if err := cli.MoveDocument(docID, targetID, moveType); err != nil {
		return err
	}

	fmt.Printf("✓ Document %s moved successfully.\n", docID)
	return nil
}

// Helper functions

func getDocTypeName(t string) string {
	if t == "2" {
		return "Directory"
	}
	return "Page"
}

func fetchAllDocs(cli *client.MMWikiClient, spaceID string, docMap map[string][]map[string]string, parentID string) ([]map[string]string, error) {
	var allDocs []map[string]string

	children := docMap[parentID]
	for _, child := range children {
		allDocs = append(allDocs, child)
		// Recursively fetch children
		childID := child["id"]
		subDocs, err := fetchAllDocs(cli, spaceID, docMap, childID)
		if err != nil {
			return nil, err
		}
		allDocs = append(allDocs, subDocs...)
	}

	return allDocs, nil
}

func printDocTree(docs []map[string]string, parentID string, level int) {
	for _, doc := range docs {
		if doc["parent_id"] == parentID || (parentID == "0" && doc["parent_id"] == "") {
			prefix := strings.Repeat("  ", level)
			icon := "📄"
			if doc["type"] == "2" {
				icon = "📁"
			}
			fmt.Printf("%s%s %s (ID: %s)\n", prefix, icon, doc["name"], doc["id"])
			printDocTree(docs, doc["id"], level+1)
		}
	}
}
