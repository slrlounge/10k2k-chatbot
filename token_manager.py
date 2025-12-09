"""
Token Management Utility
Use this script to create, list, and manage access tokens for users
"""
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Token storage file (use database in production)
TOKEN_FILE = Path("tokens.json")


def load_tokens():
    """Load tokens from file"""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_tokens(tokens):
    """Save tokens to file"""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)


def create_token(user_id: str, expires_in_days: int = 30):
    """Create a new access token"""
    import secrets
    token = secrets.token_urlsafe(32)
    tokens = load_tokens()
    
    expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
    
    tokens[token] = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at,
        "active": True
    }
    
    save_tokens(tokens)
    return token, expires_at


def revoke_token(token: str):
    """Revoke a token"""
    tokens = load_tokens()
    if token in tokens:
        tokens[token]["active"] = False
        save_tokens(tokens)
        return True
    return False


def list_tokens():
    """List all tokens"""
    tokens = load_tokens()
    return tokens


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python token_manager.py create <user_id> [expires_in_days]")
        print("  python token_manager.py list")
        print("  python token_manager.py revoke <token>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Error: user_id required")
            sys.exit(1)
        
        user_id = sys.argv[2]
        expires_in_days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        
        token, expires_at = create_token(user_id, expires_in_days)
        print("\n" + "="*60)
        print("✅ Token Created Successfully!")
        print("="*60)
        print(f"User ID:     {user_id}")
        print(f"Token:       {token}")
        print(f"Expires At:  {expires_at}")
        print("="*60)
        print("\n⚠️  IMPORTANT: Save this token securely. It won't be shown again!")
        
    elif command == "list":
        tokens = list_tokens()
        if not tokens:
            print("No tokens found.")
        else:
            print("\n" + "="*80)
            print(f"{'Token (first 16 chars)':<20} {'User ID':<20} {'Status':<10} {'Expires At':<20}")
            print("="*80)
            for token, data in tokens.items():
                token_preview = token[:16] + "..."
                status = "✅ Active" if data.get("active", True) else "❌ Revoked"
                expires_at = data.get("expires_at", "Never")
                print(f"{token_preview:<20} {data['user_id']:<20} {status:<10} {expires_at:<20}")
            print("="*80)
    
    elif command == "revoke":
        if len(sys.argv) < 3:
            print("Error: token required")
            sys.exit(1)
        
        token = sys.argv[2]
        if revoke_token(token):
            print(f"✅ Token revoked successfully")
        else:
            print(f"❌ Token not found")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()

