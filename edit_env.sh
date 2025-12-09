#!/bin/bash

# Helper script to edit .env file

echo "=========================================="
echo "  Edit .env File"
echo "=========================================="
echo ""
echo "Choose an editor:"
echo "1. nano (terminal editor - easiest)"
echo "2. VS Code (if installed)"
echo "3. TextEdit (macOS default)"
echo "4. vim (advanced)"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        nano .env
        ;;
    2)
        code .env
        ;;
    3)
        open -a TextEdit .env
        ;;
    4)
        vim .env
        ;;
    *)
        echo "Invalid choice. Opening with nano..."
        nano .env
        ;;
esac

echo ""
echo "✅ Done editing .env file"
echo ""
echo "To verify your changes, run:"
echo "  cat .env | grep GEMINI_API_KEY"

