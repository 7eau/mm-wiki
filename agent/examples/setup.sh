#!/bin/bash
# MM-Wiki CLI Setup Example
# This script demonstrates basic setup of a wiki space with documents

set -e

# Configuration
URL=${1:-"http://localhost:8081"}
USERNAME=${2:-"admin"}
PASSWORD=${3:-"password"}
CLI="${CLI:-./mmwiki-cli}"

echo "=== MM-Wiki CLI Setup Example ==="
echo "URL: $URL"
echo "Username: $USERNAME"
echo ""

# Step 1: Login
echo "[1/6] Logging in..."
$CLI login --url "$URL" --username "$USERNAME" --password "$PASSWORD"

# Step 2: Create a new space
echo ""
echo "[2/6] Creating space..."
$CLI space create \
    --name "Documentation" \
    --description "Project documentation space" \
    --tags "docs,project" \
    --level public \
    --owner 1 || echo "Space may already exist, continuing..."

# Step 3: Get space ID
echo ""
echo "[3/6] Getting space ID..."
SPACE_ID=$($CLI space list | grep "Documentation" | awk '{print $1}')
echo "Space ID: $SPACE_ID"

# Step 4: Create document structure
echo ""
echo "[4/6] Creating document structure..."

# Create directories
$CLI doc create --space "$SPACE_ID" --parent 0 --name "Getting Started" --type dir
$CLI doc create --space "$SPACE_ID" --parent 0 --name "API Reference" --type dir
$CLI doc create --space "$SPACE_ID" --parent 0 --name "User Guide" --type dir

# Step 5: Create some pages
echo ""
echo "[5/6] Creating pages..."

# Find directory IDs
GETTING_STARTED_ID=$($CLI doc list --space "$SPACE_ID" --parent 0 | grep "Getting Started" | awk '{print $1}')
API_REF_ID=$($CLI doc list --space "$SPACE_ID" --parent 0 | grep "API Reference" | awk '{print $1}')

# Create pages under Getting Started
$CLI doc create --space "$SPACE_ID" --parent "$GETTING_STARTED_ID" --name "Introduction" --type page
$CLI doc create --space "$SPACE_ID" --parent "$GETTING_STARTED_ID" --name "Installation" --type page

# Create pages under API Reference
$CLI doc create --space "$SPACE_ID" --parent "$API_REF_ID" --name "Authentication" --type page
$CLI doc create --space "$SPACE_ID" --parent "$API_REF_ID" --name "Endpoints" --type page

# Step 6: Write content to some pages
echo ""
echo "[6/6] Writing content..."

# Get page IDs
INTRO_ID=$($CLI doc list --space "$SPACE_ID" --parent "$GETTING_STARTED_ID" | grep "Introduction" | awk '{print $1}')
AUTH_ID=$($CLI doc list --space "$SPACE_ID" --parent "$API_REF_ID" | grep "Authentication" | awk '{print $1}')

# Write introduction content
cat > /tmp/intro.md << 'EOF'
# Introduction

Welcome to our project documentation!

## Overview

This documentation covers:
- Getting started guide
- API reference
- User manual
- Best practices

## Quick Links

- [Installation](Installation)
- [API Authentication](Authentication)

---

Last updated: $(date)
EOF

$CLI doc write --id "$INTRO_ID" --file /tmp/intro.md --comment "Initial setup"

# Write authentication content
cat > /tmp/auth.md << 'EOF'
# Authentication

## API Key

All API requests require an API key passed in the header:

```
Authorization: Bearer YOUR_API_KEY
```

## Obtaining API Keys

Contact your administrator to get an API key for your account.

## Rate Limiting

- 1000 requests per hour for authenticated users
- 100 requests per hour for anonymous users
EOF

$CLI doc write --id "$AUTH_ID" --file /tmp/auth.md --comment "Initial setup"

# Cleanup
rm -f /tmp/intro.md /tmp/auth.md

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Created structure:"
$CLI doc tree --space "$SPACE_ID"
