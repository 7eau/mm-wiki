package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// MMWikiClient is the HTTP client for MM-Wiki API
type MMWikiClient struct {
	BaseURL    string
	HTTPClient *http.Client
	jar        *cookiejar.Jar
	configPath string
	username   string
	loggedIn   bool
}

// Response is the standard MM-Wiki API response
type Response struct {
	Code     int                    `json:"code"`
	Message  string                 `json:"message"`
	Data     interface{}            `json:"data"`
	Redirect map[string]interface{} `json:"redirect"`
}

// NewClient creates a new MM-Wiki client
func NewClient(baseURL string) (*MMWikiClient, error) {
	// Ensure baseURL has no trailing slash
	baseURL = strings.TrimRight(baseURL, "/")

	// Create cookie jar
	jar, err := cookiejar.New(nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create cookie jar: %v", err)
	}

	client := &MMWikiClient{
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Jar:     jar,
			Timeout: 30 * time.Second,
		},
		jar:        jar,
		configPath: getConfigPath(),
	}

	// Try to load saved session
	client.loadSession()

	return client, nil
}

// Login authenticates with the MM-Wiki server
func (c *MMWikiClient) Login(username, password string) error {
	// Send plain text password - server will do MD5 encode
	data := url.Values{}
	data.Set("username", username)
	data.Set("password", password)

	resp, err := c.PostForm("/author/login", data)
	if err != nil {
		return err
	}

	if resp.Code != 1 {
		return fmt.Errorf("login failed: %s", resp.Message)
	}

	c.username = username
	c.loggedIn = true
	c.saveSession()

	return nil
}

// Logout clears the session
func (c *MMWikiClient) Logout() error {
	_, err := c.Get("/author/logout")
	if err != nil {
		return err
	}

	c.username = ""
	c.loggedIn = false
	c.clearSession()

	return nil
}

// IsLoggedIn returns true if the client has an active session
func (c *MMWikiClient) IsLoggedIn() bool {
	if !c.loggedIn {
		return false
	}

	// Verify session by calling an authenticated endpoint
	resp, err := c.Get("/main/index")
	if err != nil {
		return false
	}

	// If we get redirected to login page, session is invalid
	if resp.Redirect != nil {
		if url, ok := resp.Redirect["url"].(string); ok && strings.Contains(url, "author") {
			c.loggedIn = false
			return false
		}
	}

	return true
}

// Get performs a GET request
func (c *MMWikiClient) Get(path string) (*Response, error) {
	fullURL := c.BaseURL + path

	req, err := http.NewRequest("GET", fullURL, nil)
	if err != nil {
		return nil, err
	}

	return c.doRequest(req)
}

// PostForm performs a POST request with form data
func (c *MMWikiClient) PostForm(path string, data url.Values) (*Response, error) {
	fullURL := c.BaseURL + path

	req, err := http.NewRequest("POST", fullURL, strings.NewReader(data.Encode()))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	return c.doRequest(req)
}

// PostJSON performs a POST request with JSON data
func (c *MMWikiClient) PostJSON(path string, data interface{}) (*Response, error) {
	fullURL := c.BaseURL + path

	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", fullURL, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")

	return c.doRequest(req)
}

// doRequest performs the HTTP request and parses the response
func (c *MMWikiClient) doRequest(req *http.Request) (*Response, error) {
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	// Parse response
	var result Response
	if err := json.Unmarshal(body, &result); err != nil {
		// Not a JSON response, might be HTML page
		return &Response{
			Code:    0,
			Message: string(body),
			Data:    nil,
		}, nil
	}

	return &result, nil
}

// Session persistence
func getConfigPath() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	return filepath.Join(home, ".mmwiki-cli")
}

type sessionData struct {
	BaseURL  string    `json:"base_url"`
	Username string    `json:"username"`
	Cookies  []cookie  `json:"cookies"`
	Expires  time.Time `json:"expires"`
}

type cookie struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

func (c *MMWikiClient) saveSession() {
	// Get cookies from jar
	u, _ := url.Parse(c.BaseURL)
	cookies := c.jar.Cookies(u)

	var cookieList []cookie
	for _, ck := range cookies {
		cookieList = append(cookieList, cookie{
			Name:  ck.Name,
			Value: ck.Value,
		})
	}

	data := sessionData{
		BaseURL:  c.BaseURL,
		Username: c.username,
		Cookies:  cookieList,
		Expires:  time.Now().Add(24 * time.Hour),
	}

	jsonData, _ := json.Marshal(data)
	os.WriteFile(c.configPath, jsonData, 0600)
}

func (c *MMWikiClient) loadSession() bool {
	data, err := os.ReadFile(c.configPath)
	if err != nil {
		return false
	}

	var session sessionData
	if err := json.Unmarshal(data, &session); err != nil {
		return false
	}

	// Check if session expired
	if time.Now().After(session.Expires) {
		c.clearSession()
		return false
	}

	// Restore cookies
	u, _ := url.Parse(session.BaseURL)
	var cookies []*http.Cookie
	for _, ck := range session.Cookies {
		cookies = append(cookies, &http.Cookie{
			Name:  ck.Name,
			Value: ck.Value,
		})
	}
	c.jar.SetCookies(u, cookies)

	c.BaseURL = session.BaseURL
	c.username = session.Username
	c.loggedIn = true

	return true
}

func (c *MMWikiClient) clearSession() {
	os.Remove(c.configPath)
}

// GetUsername returns the current logged-in username
func (c *MMWikiClient) GetUsername() string {
	return c.username
}

// GetBaseURL returns the configured base URL
func (c *MMWikiClient) GetBaseURL() string {
	return c.BaseURL
}
