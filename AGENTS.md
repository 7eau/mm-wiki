# MM-Wiki Project Guide for AI Agents

## Project Overview

MM-Wiki is a lightweight enterprise knowledge sharing and team collaboration software. It helps teams quickly build an enterprise Wiki and knowledge sharing platform for information sharing and document management.

- **Repository**: https://github.com/phachon/mm-wiki
- **Version**: v0.2.2
- **License**: MIT
- **Author**: phachon (phachon@163.com)

## Technology Stack

### Backend
- **Language**: Go (Golang) 1.12+
- **Web Framework**: [Beego](https://beego.me/) v1.12.0 (MVC pattern)
- **Database**: MySQL 5.7+
- **ORM**: go-activerecord v0.0.0-20190813031814
- **Session**: Supports file, memory, memcache, redis, redis_cluster
- **Authentication**: LDAP, HTTP/HTTPS, internal database

### Frontend
- **UI Framework**: Bootstrap 3.x
- **Markdown Editor**: Editor.md
- **Icons**: Font Awesome, Glyphicons
- **jQuery Plugins**: zTree, layer, metisMenu, morris, etc.
- **Template Engine**: Go html/template (Beego's built-in)

### Infrastructure
- **Build Tool**: Go Modules + Shell scripts
- **Container**: Docker (Dockerfile included)
- **Logging**: Beego logs (console + file)
- **Email**: gomail.v2

## Project Structure

```
mm-wiki/
├── app/                    # Main application code
│   ├── bootstrap.go        # Application initialization (config, DB, dirs)
│   ├── controllers/        # HTTP handlers (MVC Controller layer)
│   │   ├── base.go         # Base controller with auth, logging
│   │   ├── template.go     # Template rendering, JSON responses
│   │   ├── author.go       # Login/logout authentication
│   │   ├── main.go         # Dashboard, home page
│   │   ├── space.go        # Space management
│   │   ├── document.go     # Document CRUD operations
│   │   ├── page.go         # Document display/view
│   │   ├── user.go         # User profile operations
│   │   ├── collection.go   # User collections/favorites
│   │   ├── follow.go       # Document/user following
│   │   ├── attachment.go   # File attachments
│   │   └── image.go        # Image upload/management
│   ├── models/             # Data access layer (MVC Model layer)
│   │   ├── init.go         # Database group initialization
│   │   ├── user.go         # User model
│   │   ├── space.go        # Space model
│   │   ├── document.go     # Document model
│   │   ├── role.go         # Role model
│   │   ├── privilege.go    # Permission model
│   │   └── ...             # Other models
│   ├── modules/            # Sub-modules
│   │   └── system/         # Admin system module
│   │       └── controllers/# System management controllers
│   ├── services/           # Business logic layer
│   │   ├── auth_login.go   # Authentication service interface
│   │   ├── auth_login_ldap.go # LDAP implementation
│   │   ├── auth_login_http.go # HTTP auth implementation
│   │   └── doc_index.go    # Document indexing service
│   ├── utils/              # Utility functions
│   │   ├── encrypt.go      # MD5, Base64 encoding
│   │   ├── file.go         # File operations
│   │   ├── email.go        # Email sending
│   │   ├── paginator.go    # Pagination
│   │   └── ...
│   └── work/               # Background workers
│       └── doc_search.go   # Document search worker
├── global/                 # Global constants
│   ├── system.go           # Version, copyright
│   └── search.go           # Search engine globals
├── install/                # Installation wizard
│   ├── main.go             # Install entry point
│   ├── router.go           # Install routes
│   ├── controllers/        # Install handlers
│   └── storage/            # Install data/storage
├── conf/                   # Configuration files
│   ├── default.conf        # Default configuration template
│   └── template.conf       # Install wizard template
├── views/                  # HTML templates (MVC View layer)
│   ├── layouts/            # Layout templates
│   ├── author/             # Login pages
│   ├── main/               # Dashboard
│   ├── space/              # Space pages
│   ├── document/           # Document pages
│   └── system/             # Admin pages
├── static/                 # Static assets
│   ├── css/                # Stylesheets
│   ├── js/                 # JavaScript files
│   ├── images/             # Image assets
│   └── plugins/            # Third-party JS plugins
├── docs/                   # Documentation
│   ├── databases/          # SQL files
│   │   ├── table.sql       # Database schema
│   │   └── data.sql        # Initial data
│   └── search_dict/        # Search dictionary files
├── scripts/                # Utility scripts
│   └── run.sh              # Start/stop script
├── router.go               # Main application routing
├── main.go                 # Application entry point
├── build.sh                # Build script
├── pack.sh                 # Cross-platform packaging
├── Dockerfile              # Docker build
└── go.mod                  # Go module dependencies
```

## Build Commands

### Prerequisites
- Go 1.12 or higher
- MySQL 5.7 or higher
- Git

### Development Build
```bash
# Clone repository
git clone https://github.com/phachon/mm-wiki.git
cd mm-wiki

# Enable Go modules
export GO111MODULE=on

# Build main application
go build -o mm-wiki ./

# Build install wizard
cd install && go build -o install ./ && cd ..
```

### Production Build
```bash
# Build for current platform
./build.sh

# Build for specific platform
GOOS=linux GOARCH=amd64 ./build.sh
GOOS=windows GOARCH=amd64 ./build.sh
GOOS=darwin GOARCH=amd64 ./build.sh

# Cross-platform packaging
./pack.sh all          # Build all platforms
./pack.sh linux        # Build Linux only
./pack.sh windows      # Build Windows only
./pack.sh darwin       # Build macOS only
```

### Docker Build
```bash
# Build Docker image
docker build -t mm-wiki .

# Run container
docker run -d -p 8080:8081 \
  -v /data/mm-wiki/conf/:/opt/mm-wiki/conf/ \
  -v /data/mm-wiki/data:/data/mm-wiki/data/ \
  --name mm-wiki mm-wiki
```

## Run Commands

### Development Mode
```bash
# Run with default config
./mm-wiki

# Run with specific config
./mm-wiki --conf conf/mm-wiki.conf

# Check version
./mm-wiki --version

# Upgrade database
./mm-wiki --conf conf/mm-wiki.conf --upgrade
```

### Production Mode
```bash
# Using run.sh script
./run.sh start      # Start service
./run.sh stop       # Stop service
./run.sh restart    # Restart service
./run.sh status     # Check status

# Or run directly with nohup
nohup ./mm-wiki --conf conf/mm-wiki.conf &
```

### Installation Wizard
```bash
# Run installer (default port 8090)
cd install && ./install

# Custom port
cd install && ./install --port=8087

# Then open http://ip:8090 in browser
```

## Testing

### Run Tests
```bash
# Run all tests
go test ./...

# Run specific package tests
go test ./app/utils/...

# Run with verbose output
go test -v ./app/utils/...
```

### Test Files
- `app/utils/version_compare_test.go` - Version comparison tests
- `app/utils/zipx_test.go` - ZIP utility tests

Note: The project has limited test coverage. Most testing is done manually.

## Configuration

### Main Configuration (conf/mm-wiki.conf)
```ini
# Run mode: prod, dev, test
runmode = "prod"
httpaddr = "0.0.0.0"
httpport = 8081

# Session
sessionon = true
sessionname = "mmwikissid"
sessionprovider = "file"
sessionproviderconfig = ".mmwiki.sessions"

# Database
[db]
host = "127.0.0.1"
port = "3306"
name = "mm_wiki"
user = "root"
pass = "password"
table_prefix = "mw_"

# Document storage
[document]
root_dir = "./data"

# Search (disabled in v0.2.1)
[search]
interval_time = 30
batch_update_doc_num = 100
```

### Environment Variables
```bash
# For China users (network proxy)
export GO111MODULE=on
export GOPROXY=https://goproxy.cn,direct
```

## Code Style Guidelines

### Go Code
1. **Naming**: 
   - Public functions/variables: PascalCase (e.g., `GetUserById`)
   - Private functions/variables: camelCase (e.g., `getUserById`)
   - Constants: UPPER_SNAKE_CASE (e.g., `USER_DELETE_TRUE`)

2. **Error Handling**: Always check errors and return early
   ```go
   rs, err = db.Query(db.AR().From(Table_User_Name).Where(...))
   if err != nil {
       return
   }
   ```

3. **Controller Pattern**: 
   - Embed `TemplateController` or `BaseController`
   - Use `this.Data["key"]` to pass data to views
   - Use `this.JsonSuccess()` / `this.JsonError()` for AJAX responses

4. **Model Pattern**:
   - Define table name constant: `Table_User_Name`
   - Define model struct and singleton: `type User struct{}`, `var UserModel = User{}`
   - Use `G.DB()` to get database connection
   - Use `go-activerecord` query builder

### Database
- Table prefix: `mw_`
- Soft delete pattern: `is_delete` field (0 = false, 1 = true)
- Timestamps: `create_time`, `update_time` (Unix timestamp)

## Security Considerations

1. **Authentication**: 
   - Passwords are MD5 hashed (lowercase)
   - Session + Cookie based authentication
   - LDAP/HTTP external authentication supported

2. **Authorization**:
   - RBAC (Role-Based Access Control)
   - Three system roles: Super Admin (1), Admin (2), User (3)
   - Space-level permissions: Visitor, Editor, Manager

3. **File Uploads**:
   - Images and attachments stored in document directory
   - File type validation recommended

4. **SQL Injection**:
   - Uses parameterized queries via go-activerecord
   - Avoid string concatenation in SQL

5. **XSS Prevention**:
   - Beego's auto-escaping in templates
   - Use `beego.Str2html()` carefully for trusted HTML

## Database Schema

### Core Tables
- `mw_user` - Users
- `mw_role` - Roles
- `mw_privilege` - Permissions
- `mw_role_privilege` - Role-Permission mapping
- `mw_space` - Spaces (document collections)
- `mw_space_user` - Space-User membership
- `mw_document` - Documents/pages
- `mw_collection` - User favorites
- `mw_follow` - User follows
- `mw_log` - System logs
- `mw_log_document` - Document change logs
- `mw_email` - Email server config
- `mw_login_auth` - External auth config
- `mw_config` - System configuration
- `mw_attachment` - File attachments

See `docs/databases/table.sql` and `docs/databases/data.sql` for full schema.

## Deployment Process

### Fresh Installation
1. Download release package
2. Extract: `tar -zxvf mm-wiki-linux-amd64.tar.gz`
3. Run installer: `cd install && ./install --port=8090`
4. Complete web installation at `http://ip:8090`
5. Start service: `./mm-wiki --conf conf/mm-wiki.conf`

### Upgrade
1. Backup database and document directory
2. Download and extract new version
3. Run upgrade: `./mm-wiki --conf conf/mm-wiki.conf --upgrade`
4. Start service: `./mm-wiki --conf conf/mm-wiki.conf`

### Nginx Reverse Proxy
```nginx
upstream frontends {
    server 127.0.0.1:8081;
}
server {
    listen 80;
    server_name wiki.example.com;
    location / {
        proxy_pass_header Server;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_pass http://frontends;
    }
    location /static {
        root /www/mm-wiki;
        expires 1d;
        add_header Cache-Control public;
        access_log off;
    }
}
```

## Common Development Tasks

### Add a New Controller
1. Create file in `app/controllers/`
2. Embed `BaseController`
3. Add routes in `router.go`
4. Create corresponding views in `views/`

### Add a New Model
1. Create file in `app/models/`
2. Define table name constant
3. Create struct and singleton instance
4. Implement CRUD methods using `G.DB()`

### Add a New Page
1. Add controller action
2. Create template in `views/[controller]/`
3. Use layout: `this.viewLayout("page_name", "layout_name")`

## Important Notes

1. **Full-text search is disabled** in v0.2.1 (see CHANGELOG)
2. **Document storage**: Markdown files stored in `document.root_dir` (default: `./data`)
3. **Session storage**: Default is file-based; use Redis for production clusters
4. **LDAP support**: Implemented in `app/services/auth_login_ldap.go`
5. **Email notifications**: Require SMTP configuration in system settings

## AI Agent Tools

The `agent/` directory contains CLI tools and skills for AI agents to interact with MM-Wiki:

```
agent/
├── cli/              # Command-line interface tool
│   ├── client/       # HTTP API client library
│   ├── cmd/          # CLI command implementations
│   ├── main.go       # Entry point
│   ├── go.mod        # Go module definition
│   └── Makefile      # Build automation
├── skills/           # Skill documentation for AI agents
│   └── SKILL.md      # Comprehensive usage guide
└── examples/         # Example scripts
    ├── setup.sh      # Basic setup example
    └── backup.sh     # Backup export script
```

### Building the CLI Tool

```bash
cd agent/cli
make build
# Or: go build -o mmwiki-cli ./
```

### Basic Usage

```bash
# Login
./mmwiki-cli login --url http://wiki.example.com:8081 --username admin --password secret

# List users
./mmwiki-cli user list

# Create space
./mmwiki-cli space create --name "My Project" --description "Docs" --owner 1

# List documents
./mmwiki-cli doc list --space 1

# Read document
./mmwiki-cli doc read --id 123
```

### Key Features

- **Session-based authentication** - Login once, session saved to `~/.mmwiki-cli`
- **User management** - List, create, update, delete users
- **Space management** - Manage wiki spaces
- **Document operations** - CRUD, tree view, read/write content
- **HTTP API based** - Works with any deployed MM-Wiki instance

See `agent/skills/SKILL.md` for complete documentation.

## Resources

- **Documentation**: README.md, README_eng.md
- **Changelog**: CHANGELOG.md
- **Issue Tracking**: GitHub Issues
- **Community**: QQ Group 853467682 (Chinese)
