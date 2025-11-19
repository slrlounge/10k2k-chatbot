#!/usr/bin/env python3
"""
Quick script to generate tokens for Kajabi members.

Usage:
    python3 generate_token.py <user_id> [expiration_minutes]

Examples:
    python3 generate_token.py kajabi_user_12345
    python3 generate_token.py kajabi_user_12345 1440  # 24 hours
    python3 generate_token.py kajabi_user_12345 10080  # 7 days
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from auth.token_utils import generate_token

load_dotenv()

def main():
    if len(sys.argv) < 2:
        print("\n" + "="*70)
        print("🔑 KAJABI TOKEN GENERATOR")
        print("="*70)
        print()
        print("Usage:")
        print("  python3 generate_token.py <user_id> [expiration_minutes]")
        print()
        print("Examples:")
        print("  python3 generate_token.py kajabi_user_12345")
        print("  python3 generate_token.py kajabi_user_12345 1440  # 24 hours")
        print("  python3 generate_token.py kajabi_user_12345 10080  # 7 days")
        print()
        print("="*70)
        sys.exit(1)
    
    user_id = sys.argv[1]
    expiration_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 1440  # Default: 24 hours
    
    try:
        token = generate_token(user_id, expiration_minutes)
        chatbot_url = f"https://chatbot-api-odi0.onrender.com/web/chat.html?token={token}"
        
        print("\n" + "="*70)
        print("✅ TOKEN GENERATED SUCCESSFULLY")
        print("="*70)
        print()
        print(f"User ID:     {user_id}")
        print(f"Expiration: {expiration_minutes} minutes ({expiration_minutes/60:.1f} hours)")
        print()
        print("Token:")
        print(f"  {token}")
        print()
        print("Full URL:")
        print(f"  {chatbot_url}")
        print()
        print("="*70)
        print("📋 COPY THIS TOKEN FOR KAJABI EMBEDDING")
        print("="*70)
        print()
        print("HTML Code:")
        print("-" * 70)
        print(f'<iframe src="{chatbot_url}" width="100%" height="800px" frameborder="0"></iframe>')
        print("-" * 70)
        print()
        
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure AUTH_SECRET_KEY is set in your .env file!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

