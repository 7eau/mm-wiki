package client

import (
	"fmt"
	"net/url"
	"strconv"
)

// ==================== User APIs ====================

// User represents a user in the system
type User struct {
	UserID      string `json:"user_id"`
	Username    string `json:"username"`
	Name        string `json:"name"`
	Email       string `json:"email"`
	Phone       string `json:"phone"`
	RoleID      string `json:"role_id"`
	IsForbidden string `json:"is_forbidden"`
	LastTime    string `json:"last_time"`
	CreateTime  string `json:"create_time"`
}

// ListUsers returns a list of users
func (c *MMWikiClient) ListUsers(keywords string, limit, offset int) ([]User, error) {
	data := url.Values{}
	data.Set("limit", fmt.Sprintf("%d", limit))
	data.Set("number", fmt.Sprintf("%d", offset))
	if keywords != "" {
		data.Set("keywords", keywords)
	}

	resp, err := c.PostForm("/system/user/lists", data)
	if err != nil {
		return nil, err
	}

	if resp.Code != 1 {
		return nil, fmt.Errorf("%s", resp.Message)
	}

	// Parse user list from response
	users := []User{}
	if list, ok := resp.Data.([]interface{}); ok {
		for _, item := range list {
			if m, ok := item.(map[string]interface{}); ok {
				users = append(users, mapToUser(m))
			}
		}
	}

	return users, nil
}

// GetUser gets a user by ID
func (c *MMWikiClient) GetUser(userID string) (*User, error) {
	data := url.Values{}
	data.Set("user_id", userID)

	resp, err := c.PostForm("/system/user/detail", data)
	if err != nil {
		return nil, err
	}

	if resp.Code != 1 {
		return nil, fmt.Errorf("%s", resp.Message)
	}

	if m, ok := resp.Data.(map[string]interface{}); ok {
		user := mapToUser(m)
		return &user, nil
	}

	return nil, fmt.Errorf("user not found")
}

// CreateUser creates a new user
func (c *MMWikiClient) CreateUser(username, password, name, email, phone string, roleID int) error {
	data := url.Values{}
	data.Set("username", username)
	data.Set("password", password)
	data.Set("name", name)
	data.Set("email", email)
	data.Set("phone", phone)
	data.Set("role_id", fmt.Sprintf("%d", roleID))

	resp, err := c.PostForm("/system/user/save", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

// UpdateUser updates a user
func (c *MMWikiClient) UpdateUser(userID, name, email, phone string, roleID int) error {
	data := url.Values{}
	data.Set("user_id", userID)
	data.Set("name", name)
	data.Set("email", email)
	data.Set("phone", phone)
	data.Set("role_id", fmt.Sprintf("%d", roleID))

	resp, err := c.PostForm("/system/user/modify", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

// DeleteUser deletes a user
func (c *MMWikiClient) DeleteUser(userID string) error {
	data := url.Values{}
	data.Set("user_id", userID)

	resp, err := c.PostForm("/system/user/delete", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

func mapToUser(m map[string]interface{}) User {
	return User{
		UserID:      getString(m, "user_id"),
		Username:    getString(m, "username"),
		Name:        getString(m, "name"),
		Email:       getString(m, "email"),
		Phone:       getString(m, "phone"),
		RoleID:      getString(m, "role_id"),
		IsForbidden: getString(m, "is_forbidden"),
		LastTime:    getString(m, "last_time"),
		CreateTime:  getString(m, "create_time"),
	}
}

// ==================== Space APIs ====================

// Space represents a space in the system
type Space struct {
	SpaceID     string `json:"space_id"`
	Name        string `json:"name"`
	Description string `json:"description"`
	Tags        string `json:"tags"`
	VisitLevel  string `json:"visit_level"`
	UserID      string `json:"user_id"`
	IsShare     string `json:"is_share"`
	IsDownload  string `json:"is_download"`
	CreateTime  string `json:"create_time"`
}

// ListSpaces returns a list of spaces
func (c *MMWikiClient) ListSpaces(limit, offset int) ([]Space, error) {
	data := url.Values{}
	data.Set("limit", fmt.Sprintf("%d", limit))
	data.Set("number", fmt.Sprintf("%d", offset))

	resp, err := c.PostForm("/system/space/lists", data)
	if err != nil {
		return nil, err
	}

	if resp.Code != 1 {
		return nil, fmt.Errorf("%s", resp.Message)
	}

	spaces := []Space{}
	if list, ok := resp.Data.([]interface{}); ok {
		for _, item := range list {
			if m, ok := item.(map[string]interface{}); ok {
				spaces = append(spaces, mapToSpace(m))
			}
		}
	}

	return spaces, nil
}

// GetSpace gets a space by ID
func (c *MMWikiClient) GetSpace(spaceID string) (*Space, error) {
	data := url.Values{}
	data.Set("space_id", spaceID)

	resp, err := c.PostForm("/system/space/detail", data)
	if err != nil {
		return nil, err
	}

	if resp.Code != 1 {
		return nil, fmt.Errorf("%s", resp.Message)
	}

	if m, ok := resp.Data.(map[string]interface{}); ok {
		space := mapToSpace(m)
		return &space, nil
	}

	return nil, fmt.Errorf("space not found")
}

// CreateSpace creates a new space
func (c *MMWikiClient) CreateSpace(name, description, tags, visitLevel string, ownerID int) error {
	data := url.Values{}
	data.Set("name", name)
	data.Set("description", description)
	data.Set("tags", tags)
	data.Set("visit_level", visitLevel)
	data.Set("user_id", fmt.Sprintf("%d", ownerID))

	resp, err := c.PostForm("/system/space/save", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

// UpdateSpace updates a space
func (c *MMWikiClient) UpdateSpace(spaceID, name, description, tags, visitLevel string) error {
	data := url.Values{}
	data.Set("space_id", spaceID)
	data.Set("name", name)
	data.Set("description", description)
	data.Set("tags", tags)
	data.Set("visit_level", visitLevel)

	resp, err := c.PostForm("/system/space/modify", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

// DeleteSpace deletes a space
func (c *MMWikiClient) DeleteSpace(spaceID string) error {
	data := url.Values{}
	data.Set("space_id", spaceID)

	resp, err := c.PostForm("/system/space/delete", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

func mapToSpace(m map[string]interface{}) Space {
	return Space{
		SpaceID:     getString(m, "space_id"),
		Name:        getString(m, "name"),
		Description: getString(m, "description"),
		Tags:        getString(m, "tags"),
		VisitLevel:  getString(m, "visit_level"),
		UserID:      getString(m, "user_id"),
		IsShare:     getString(m, "is_share"),
		IsDownload:  getString(m, "is_download"),
		CreateTime:  getString(m, "create_time"),
	}
}

// ==================== Document APIs ====================

// Document represents a document in the system
type Document struct {
	DocumentID   string `json:"document_id"`
	SpaceID      string `json:"space_id"`
	ParentID     string `json:"parent_id"`
	Name         string `json:"name"`
	Type         string `json:"type"`
	Path         string `json:"path"`
	Sequence     string `json:"sequence"`
	CreateUserID string `json:"create_user_id"`
	EditUserID   string `json:"edit_user_id"`
	CreateTime   string `json:"create_time"`
	UpdateTime   string `json:"update_time"`
}

// DocumentContent holds document content
type DocumentContent struct {
	Document
	Content string `json:"content"`
}

// ListDocuments returns a list of documents in a space
func (c *MMWikiClient) ListDocuments(spaceID, parentID string) ([]Document, error) {
	data := url.Values{}
	data.Set("space_id", spaceID)
	data.Set("parent_id", parentID)

	resp, err := c.PostForm("/document/lists", data)
	if err != nil {
		return nil, err
	}

	if resp.Code != 1 {
		return nil, fmt.Errorf("%s", resp.Message)
	}

	docs := []Document{}
	if list, ok := resp.Data.([]interface{}); ok {
		for _, item := range list {
			if m, ok := item.(map[string]interface{}); ok {
				docs = append(docs, mapToDocument(m))
			}
		}
	}

	return docs, nil
}

// GetDocument gets a document by ID
func (c *MMWikiClient) GetDocument(docID string) (*DocumentContent, error) {
	data := url.Values{}
	data.Set("document_id", docID)

	resp, err := c.PostForm("/page/display", data)
	if err != nil {
		return nil, err
	}

	if resp.Code != 1 {
		return nil, fmt.Errorf("%s", resp.Message)
	}

	if m, ok := resp.Data.(map[string]interface{}); ok {
		doc := DocumentContent{
			Document: mapToDocument(m),
			Content:  getString(m, "content"),
		}
		return &doc, nil
	}

	return nil, fmt.Errorf("document not found")
}

// GetDocumentDetail gets document detail with content
func (c *MMWikiClient) GetDocumentDetail(docID string) (*DocumentContent, error) {
	data := url.Values{}
	data.Set("document_id", docID)

	resp, err := c.PostForm("/page/edit", data)
	if err != nil {
		return nil, err
	}

	if resp.Code != 1 {
		return nil, fmt.Errorf("%s", resp.Message)
	}

	if m, ok := resp.Data.(map[string]interface{}); ok {
		doc := DocumentContent{
			Document: mapToDocument(m),
			Content:  getString(m, "content"),
		}
		return &doc, nil
	}

	return nil, fmt.Errorf("document not found")
}

// CreateDocument creates a new document
func (c *MMWikiClient) CreateDocument(spaceID, parentID, name, docType string, userID int) (*Document, error) {
	data := url.Values{}
	data.Set("space_id", spaceID)
	data.Set("parent_id", parentID)
	data.Set("name", name)
	data.Set("type", docType)
	data.Set("create_user_id", fmt.Sprintf("%d", userID))

	resp, err := c.PostForm("/document/save", data)
	if err != nil {
		return nil, err
	}

	if resp.Code != 1 {
		return nil, fmt.Errorf("%s", resp.Message)
	}

	// Return created document info
	doc := &Document{
		SpaceID:      spaceID,
		ParentID:     parentID,
		Name:         name,
		Type:         docType,
		CreateUserID: fmt.Sprintf("%d", userID),
	}

	return doc, nil
}

// UpdateDocument updates a document
func (c *MMWikiClient) UpdateDocument(docID, name string, userID int) error {
	data := url.Values{}
	data.Set("document_id", docID)
	data.Set("name", name)
	data.Set("update_user_id", fmt.Sprintf("%d", userID))

	resp, err := c.PostForm("/document/modify", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

// SaveDocumentContent saves document content
func (c *MMWikiClient) SaveDocumentContent(docID, name, content, comment string, userID int) error {
	data := url.Values{}
	data.Set("document_id", docID)
	data.Set("name", name)
	data.Set("document_page_editor-markdown-doc", content)
	data.Set("comment", comment)
	data.Set("is_notice_user", "0")
	data.Set("is_follow_doc", "1")
	data.Set("update_user_id", fmt.Sprintf("%d", userID))

	resp, err := c.PostForm("/page/save", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

// DeleteDocument deletes a document
func (c *MMWikiClient) DeleteDocument(docID string) error {
	data := url.Values{}
	data.Set("document_id", docID)

	resp, err := c.PostForm("/document/delete", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

// MoveDocument moves a document to a new parent
func (c *MMWikiClient) MoveDocument(docID, targetID, moveType string) error {
	data := url.Values{}
	data.Set("document_id", docID)
	data.Set("target_id", targetID)
	data.Set("move_type", moveType)

	resp, err := c.PostForm("/document/move", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("%s", resp.Message)
	}

	return nil
}

func mapToDocument(m map[string]interface{}) Document {
	return Document{
		DocumentID:   getString(m, "document_id"),
		SpaceID:      getString(m, "space_id"),
		ParentID:     getString(m, "parent_id"),
		Name:         getString(m, "name"),
		Type:         getString(m, "type"),
		Path:         getString(m, "path"),
		Sequence:     getString(m, "sequence"),
		CreateUserID: getString(m, "create_user_id"),
		EditUserID:   getString(m, "edit_user_id"),
		CreateTime:   getString(m, "create_time"),
		UpdateTime:   getString(m, "update_time"),
	}
}

// ==================== Helper Functions ====================

func getString(m map[string]interface{}, key string) string {
	if val, ok := m[key]; ok {
		switch v := val.(type) {
		case string:
			return v
		case float64:
			return strconv.FormatFloat(v, 'f', -1, 64)
		case int:
			return fmt.Sprintf("%d", v)
		default:
			return fmt.Sprintf("%v", v)
		}
	}
	return ""
}
