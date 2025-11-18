# Kajabi Token-Based Authentication

This module implements token-based authentication for the chatbot, ensuring only logged-in Kajabi paying members can access it.

## Overview

The authentication system uses JWT (JSON Web Tokens) to securely authenticate users coming from Kajabi. Tokens are cryptographically signed and can include expiration times.

## How It Works

### 1. Token Generation (Kajabi Side)

When a Kajabi member accesses a members-only page, Kajabi should generate a token and embed it in the chatbot iframe or link:

```python
from auth.token_utils import generate_token

# Generate token for a Kajabi member
user_id = "kajabi_user_12345"  # Get from Kajabi user data
token = generate_token(user_id, expiration_minutes=60)

# Embed in iframe URL
iframe_url = f"https://your-chatbot.com/web/chat.html?token={token}"
```

### 2. Token Validation (Chatbot Side)

The chatbot automatically:
- Reads token from URL parameter (`?token=...`)
- Stores token in localStorage for bookmarking
- Validates token on every API request
- Redirects to Kajabi login if token is invalid/expired

### 3. User Flow

**Scenario A: User clicks link from Kajabi**
1. Kajabi generates token with user_id
2. User clicks link: `chatbot.com/web/chat.html?token=abc123...`
3. Chatbot validates token → grants access
4. Token saved to localStorage for future visits

**Scenario B: User bookmarks chatbot**
1. User returns via bookmark
2. Chatbot reads token from localStorage
3. Token validated → grants access
4. If expired → redirects to Kajabi login

**Scenario C: Invalid/expired token**
1. Token validation fails
2. Chatbot redirects to Kajabi login page
3. User logs in → Kajabi generates new token → redirects back

## Configuration

Set these environment variables:

```bash
ENABLE_AUTH=true
AUTH_SECRET_KEY=your_secret_key_here_change_this
KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
TOKEN_EXPIRATION_MINUTES=60
```

**Important:** `AUTH_SECRET_KEY` must be:
- A long, random string (at least 32 characters)
- Kept secret (never commit to git)
- The same value used by Kajabi to generate tokens

## Kajabi Integration Guide

### Option 1: Iframe Embedding

In your Kajabi members-only page, embed the chatbot in an iframe:

```html
<iframe 
    src="https://your-chatbot.com/web/chat.html?token={{kajabi_token}}" 
    width="100%" 
    height="800px"
    frameborder="0">
</iframe>
```

Replace `{{kajabi_token}}` with Kajabi's token generation (see Kajabi API docs).

### Option 2: Direct Link

Create a link that includes the token:

```html
<a href="https://your-chatbot.com/web/chat.html?token={{kajabi_token}}">
    Access Chatbot
</a>
```

### Option 3: JavaScript Redirect

Use JavaScript to redirect with token:

```javascript
const token = generateToken(kajabiUserId);
window.location.href = `https://your-chatbot.com/web/chat.html?token=${token}`;
```

## Security Notes

1. **Secret Key**: Must be kept secure and never exposed
2. **HTTPS**: Always use HTTPS in production
3. **Token Expiration**: Tokens expire after configured minutes
4. **Token Storage**: Tokens stored in localStorage (consider httpOnly cookies for production)

## Testing

To test without Kajabi:

1. Generate a test token:
```python
from auth.token_utils import generate_token
token = generate_token("test_user_123")
print(f"Test token: {token}")
```

2. Access chatbot with token:
```
https://your-chatbot.com/web/chat.html?token=YOUR_TOKEN_HERE
```

3. Disable auth for development:
```bash
ENABLE_AUTH=false
```

## Troubleshooting

**Token validation fails:**
- Check that `AUTH_SECRET_KEY` matches between token generation and validation
- Verify token hasn't expired
- Check token format (should be valid JWT)

**Redirect loop:**
- Ensure `KJ_LOGIN_URL` is correct
- Check that Kajabi login page accepts redirects back to chatbot

**Auth not working:**
- Verify `ENABLE_AUTH=true` in environment
- Check that `AUTH_SECRET_KEY` is set
- Ensure PyJWT is installed: `pip install PyJWT`

