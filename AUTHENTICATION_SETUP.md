# Token-Based Authentication Setup Guide

This document explains how to set up and use the token-based authentication system for Kajabi integration.

## Overview

The chatbot now supports token-based authentication to ensure only logged-in Kajabi paying members can access it. The system uses JWT (JSON Web Tokens) for secure authentication.

## Quick Start

### 1. Install Dependencies

```bash
pip install PyJWT>=2.8.0
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Add these to your `.env` file:

```bash
# Enable/disable authentication (default: false)
ENABLE_AUTH=true

# Secret key for signing tokens (MUST be set if ENABLE_AUTH=true)
# Generate a secure random string (at least 32 characters)
AUTH_SECRET_KEY=your_super_secret_key_here_change_this_to_random_string

# Kajabi login URL for redirects
KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login

# Token expiration time in minutes (default: 60)
TOKEN_EXPIRATION_MINUTES=60
```

**Important:** Generate a secure `AUTH_SECRET_KEY`:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3. Test Authentication (Development)

To test without Kajabi, generate a test token:

```python
from auth.token_utils import generate_token

# Generate token for a test user
token = generate_token("test_user_123", expiration_minutes=60)
print(f"Test token: {token}")

# Access chatbot with token
# https://your-chatbot.com/web/chat.html?token={token}
```

### 4. Enable Authentication

Set `ENABLE_AUTH=true` in your `.env` file and restart the server.

## How It Works

### Token Flow

1. **Kajabi generates token** → User accesses members-only page
2. **Token embedded in URL** → `chatbot.com/web/chat.html?token=abc123...`
3. **Frontend stores token** → Saved to localStorage for bookmarking
4. **Token sent with requests** → Included in Authorization header
5. **Backend validates token** → Checks signature and expiration
6. **Access granted/denied** → Valid token = access, invalid = redirect to Kajabi

### Token Sources (checked in order)

1. URL query parameter: `?token=...`
2. Authorization header: `Authorization: Bearer <token>`
3. Cookie: `auth_token=<token>`

## Kajabi Integration

### Option 1: Iframe Embedding

In your Kajabi members-only page:

```html
<iframe 
    src="https://your-chatbot.com/web/chat.html?token={{kajabi_token}}" 
    width="100%" 
    height="800px"
    frameborder="0">
</iframe>
```

Replace `{{kajabi_token}}` with Kajabi's token generation.

### Option 2: Direct Link

```html
<a href="https://your-chatbot.com/web/chat.html?token={{kajabi_token}}">
    Access Chatbot
</a>
```

### Option 3: JavaScript Redirect

```javascript
// In Kajabi custom code
const token = generateKajabiToken(userId);
window.location.href = `https://your-chatbot.com/web/chat.html?token=${token}`;
```

## Token Generation (Kajabi Side)

Kajabi needs to generate tokens using the same secret key. Example implementation:

```python
from auth.token_utils import generate_token

# In Kajabi webhook or custom code
user_id = kajabi_user.id  # Get from Kajabi
token = generate_token(user_id, expiration_minutes=60)

# Embed in iframe or link
iframe_url = f"https://your-chatbot.com/web/chat.html?token={token}"
```

**Important:** Kajabi must use the same `AUTH_SECRET_KEY` to generate tokens.

## Frontend Behavior

### Automatic Token Handling

- **URL token**: Automatically extracted and saved to localStorage
- **Bookmarked links**: Token loaded from localStorage
- **Expired tokens**: Automatic redirect to Kajabi login
- **Invalid tokens**: Automatic redirect to Kajabi login

### User Experience

1. User clicks link from Kajabi → Token in URL → Saved automatically
2. User bookmarks chatbot → Token from localStorage → Works seamlessly
3. Token expires → Redirects to Kajabi login → User logs in → New token → Redirects back

## API Endpoints

### `GET /auth/check`

Check authentication status.

**Response:**
```json
{
  "authenticated": true,
  "user_id": "kajabi_user_123",
  "auth_enabled": true
}
```

### `GET /web/chat.html?token=...`

Serve chat page with token validation.

### `POST /ask`

Chat endpoint (requires authentication if `ENABLE_AUTH=true`).

**Headers:**
```
Authorization: Bearer <token>
```

Or include token in query parameter or cookie.

## Security Considerations

1. **Secret Key**: Keep `AUTH_SECRET_KEY` secure and never commit to git
2. **HTTPS**: Always use HTTPS in production
3. **Token Expiration**: Tokens expire after configured minutes
4. **Token Storage**: Tokens stored in localStorage (consider httpOnly cookies for enhanced security)

## Troubleshooting

### "Authentication required" error

- Check `ENABLE_AUTH=true` in `.env`
- Verify `AUTH_SECRET_KEY` is set
- Ensure token is being sent (check browser console)

### "Invalid or expired token" error

- Token may have expired (check `TOKEN_EXPIRATION_MINUTES`)
- Token signature doesn't match (verify `AUTH_SECRET_KEY` matches between generation and validation)
- Token format is invalid

### Redirect loop

- Verify `KJ_LOGIN_URL` is correct
- Check that Kajabi login page accepts redirects back to chatbot
- Ensure token generation is working in Kajabi

### Auth not working

- Verify `ENABLE_AUTH=true` in environment
- Check that `AUTH_SECRET_KEY` is set
- Ensure PyJWT is installed: `pip install PyJWT`
- Check server logs for warnings

## Testing

### Test Token Generation

```python
from auth.token_utils import generate_token, validate_token

# Generate
token = generate_token("test_user", expiration_minutes=60)
print(f"Token: {token}")

# Validate
try:
    payload = validate_token(token)
    print(f"Valid! User: {payload['user_id']}")
except ValueError as e:
    print(f"Invalid: {e}")
```

### Test Authentication Flow

1. Set `ENABLE_AUTH=true`
2. Generate a test token
3. Access: `http://localhost:8001/web/chat.html?token=<token>`
4. Verify token is saved to localStorage
5. Try accessing without token → should redirect
6. Try accessing with expired token → should redirect

## Disabling Authentication

To disable authentication for development:

```bash
ENABLE_AUTH=false
```

This allows unrestricted access without tokens.

