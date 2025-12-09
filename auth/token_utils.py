"""
Token-based authentication utilities for Kajabi integration.

This module handles:
- Generating signed JWT tokens for authenticated Kajabi members
- Validating tokens on incoming requests
- Token expiration and refresh logic

How Kajabi Integration Works:
1. Kajabi generates a token when a member accesses a members-only page
2. Token is embedded in iframe URL or passed as a link parameter
3. Chatbot validates the token and grants/denies access accordingly
4. Token can be stored in localStorage for bookmarking support
"""

import os
import time
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# Configuration from environment variables
AUTH_SECRET_KEY = os.getenv('AUTH_SECRET_KEY', '')
TOKEN_EXPIRATION_MINUTES = int(os.getenv('TOKEN_EXPIRATION_MINUTES', '60'))
KJ_LOGIN_URL = os.getenv('KJ_LOGIN_URL', 'https://www.slrloungeworkshops.com/login')

# Algorithm for JWT signing
ALGORITHM = 'HS256'


def generate_token(user_id: str, expiration_minutes: Optional[int] = None) -> str:
    """
    Generate a signed JWT token for a Kajabi member.
    
    Args:
        user_id: Unique identifier for the Kajabi member
        expiration_minutes: Optional custom expiration (defaults to TOKEN_EXPIRATION_MINUTES)
    
    Returns:
        Signed JWT token string
    
    Example usage from Kajabi:
        token = generate_token(user_id="kajabi_user_12345")
        chatbot_url = f"https://your-chatbot.com/web/chat.html?token={token}"
    """
    if not AUTH_SECRET_KEY:
        raise ValueError("AUTH_SECRET_KEY must be set in environment variables")
    
    expiration = expiration_minutes or TOKEN_EXPIRATION_MINUTES
    expiration_time = datetime.utcnow() + timedelta(minutes=expiration)
    
    payload = {
        'user_id': user_id,
        'iat': datetime.utcnow(),  # Issued at
        'exp': expiration_time,     # Expiration
        'source': 'kajabi'          # Token source identifier
    }
    
    token = jwt.encode(payload, AUTH_SECRET_KEY, algorithm=ALGORITHM)
    return token


def validate_token(token: str) -> Dict:
    """
    Validate a JWT token and return the payload if valid.
    
    Args:
        token: JWT token string to validate
    
    Returns:
        Dictionary containing token payload (user_id, exp, etc.)
    
    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid or malformed
    """
    if not AUTH_SECRET_KEY:
        raise ValueError("AUTH_SECRET_KEY must be set in environment variables")
    
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def is_token_valid(token: str) -> bool:
    """
    Check if a token is valid without raising exceptions.
    
    Args:
        token: JWT token string to check
    
    Returns:
        True if token is valid, False otherwise
    """
    try:
        validate_token(token)
        return True
    except (ValueError, jwt.InvalidTokenError):
        return False


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token.
    
    Args:
        token: JWT token string
    
    Returns:
        datetime object of expiration, or None if invalid
    """
    try:
        payload = validate_token(token)
        return datetime.fromtimestamp(payload['exp'])
    except (ValueError, jwt.InvalidTokenError):
        return None

