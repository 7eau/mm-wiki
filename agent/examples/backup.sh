#!/bin/bash
# MM-Wiki Backup Script
# Exports all documents from a space to local markdown files

set -e

# Configuration
URL=${1:-"http://localhost:8081"}
USERNAME=${2:-"admin"}
PASSWORD=${3:-"password"}
SPACE_ID=${4:-"1"}
BACKUP_DIR=${5:-"./mmwiki-backup"}
CLI="${CLI:-./mmwiki-cli}"

function show_usage() {
    echo "Usage: $0 <url> <username> <password> <space_id> <backup_dir>"
    echo ""
    echo "Example:"
    echo "  $0 http://localhost:8081 admin secret 1 ./backup"
    exit 1
}

if [ $# -lt 5 ]; then
    show_usage
fi

echo "=== MM-Wiki Backup Tool ==="
echo "URL: $URL"
echo "Space ID: $SPACE_ID"
echo "Backup Directory: $BACKUP_DIR"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Login
echo "[1/3] Logging in..."
$CLI login --url "$URL" --username "$USERNAME" --password "$PASSWORD"

# Get space info
echo ""
echo "[2/3] Getting space information..."
$CLI space get --id "$SPACE_ID" > "$BACKUP_DIR/space-info.txt"
SPACE_NAME=$(grep "Name:" "$BACKUP_DIR/space-info.txt" | cut -d: -f2 | xargs)
echo "Space Name: $SPACE_NAME"

# Export documents
echo ""
echo "[3/3] Exporting documents..."

# Function to recursively export documents
function export_documents() {
    local space_id=$1
    local parent_id=$2
    local path_prefix=$3

    # Get documents list
    local docs
    docs=$($CLI doc list --space "$space_id" --parent "$parent_id" 2>/dev/null || true)

    if [ -z "$docs" ] || [ "$docs" = "No documents found" ]; then
        return
    fi

    # Process each document
    echo "$docs" | tail -n +2 | head -n -2 | while read -r line; do
        # Skip header and footer lines
        if [[ "$line" =~ ^[0-9]+ ]]; then
            local doc_id=$(echo "$line" | awk '{print $1}')
            local doc_name=$(echo "$line" | awk '{print $2}')
            local doc_type=$(echo "$line" | awk '{print $3}')

            # Sanitize filename
            local safe_name=$(echo "$doc_name" | tr -cd '[:alnum:]._-')
            local file_path="$BACKUP_DIR/$path_prefix$safe_name"

            if [ "$doc_type" = "Dir" ]; then
                # Create directory
                mkdir -p "$file_path"
                echo "  [DIR] $path_prefix$doc_name/"
                
                # Recursively export children
                export_documents "$space_id" "$doc_id" "$path_prefix$safe_name/"
            else
                # Export page content
                echo "  [PAGE] $path_prefix$doc_name.md"
                $CLI doc read --id "$doc_id" --output "$file_path.md" 2>/dev/null || {
                    echo "    Warning: Failed to export document $doc_id"
                    touch "$file_path.md"
                }
            fi
        fi
    done
}

# Start export from root
export_documents "$SPACE_ID" "0" ""

# Create index file
echo ""
echo "Creating index..."
cat > "$BACKUP_DIR/README.md" << EOF
# Backup of "$SPACE_NAME"

- Space ID: $SPACE_ID
- Backup Date: $(date)
- Tool: MM-Wiki CLI

## Structure

\`\`\`
$(find "$BACKUP_DIR" -type f -name "*.md" | sort)
\`\`\`

## Notes

This backup was created automatically using mmwiki-cli.
EOF

# Summary
echo ""
echo "=== Backup Complete ==="
echo "Files exported: $(find "$BACKUP_DIR" -type f | wc -l)"
echo "Total size: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo "Location: $BACKUP_DIR"
