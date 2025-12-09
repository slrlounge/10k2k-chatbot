#!/bin/bash
# Build script for frontend - replaces API_URL in chat.html

set -e

# Get API URL from environment or use default
API_URL=${API_URL:-"https://your-api.onrender.com"}
KJ_LOGIN_URL=${KJ_LOGIN_URL:-"https://www.slrloungeworkshops.com/login"}

echo "Building frontend with API_URL: $API_URL"

# Create build directory
mkdir -p dist

# Copy web files
cp -r web/* dist/

# Replace API_URL in chat.html (for static builds)
if [ -f "dist/chat.html" ]; then
    # Use sed to replace the API_URL line
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|const API_URL = .*|const API_URL = '${API_URL}';|g" dist/chat.html
        sed -i '' "s|const KJ_LOGIN_URL = .*|const KJ_LOGIN_URL = '${KJ_LOGIN_URL}';|g" dist/chat.html
    else
        # Linux
        sed -i "s|const API_URL = .*|const API_URL = '${API_URL}';|g" dist/chat.html
        sed -i "s|const KJ_LOGIN_URL = .*|const KJ_LOGIN_URL = '${KJ_LOGIN_URL}';|g" dist/chat.html
    fi
    echo "✓ Updated API_URL in chat.html"
fi

echo "✓ Frontend build complete"
echo "✓ Files ready in dist/ directory"

