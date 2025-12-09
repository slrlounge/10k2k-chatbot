#!/bin/bash

# Quick Setup Script for RAG Chatbot

echo "=========================================="
echo "  RAG Chatbot Quick Setup"
echo "=========================================="
echo ""

# Step 1: Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp env.example .env
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "=========================================="
echo "  Next Steps:"
echo "=========================================="
echo ""
echo "1. Edit .env file and add your GEMINI_API_KEY:"
echo "   nano .env"
echo "   (or use your favorite editor)"
echo ""
echo "2. Create File Search Store:"
echo "   python create_store.py"
echo ""
echo "3. Copy the Store ID and add it to .env as GEMINI_STORE_ID"
echo ""
echo "4. Upload files to File Search Store:"
echo "   Option A: Use Google AI Studio UI (recommended)"
echo "   Option B: python upload_gcs_to_store.py"
echo ""
echo "5. Test your chatbot:"
echo "   python app.py"
echo ""
echo "=========================================="
echo "  For detailed instructions, see NEXT_STEPS.md"
echo "=========================================="


