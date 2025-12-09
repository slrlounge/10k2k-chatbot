"""
Kajabi Webhook Integration
This script handles Kajabi webhooks to automatically create/revoke tokens
when users purchase or cancel subscriptions.

To use this:
1. Set up a webhook in Kajabi that points to this endpoint
2. Configure the webhook to send events for purchases/cancellations
3. Deploy this alongside your FastAPI app
"""
import os
import hmac
import hashlib
import json
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.routing import APIRoute
from pydantic import BaseModel
from token_manager import create_token, revoke_token, load_tokens

# Initialize FastAPI app for webhook
webhook_app = FastAPI(title="Kajabi Webhook Handler")

# Get webhook secret from environment
KAJABI_WEBHOOK_SECRET = os.getenv("KAJABI_WEBHOOK_SECRET", "")


class KajabiWebhook(BaseModel):
    """Kajabi webhook payload structure"""
    event: str
    data: dict


def verify_kajabi_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Kajabi webhook signature"""
    if not secret:
        return False  # Skip verification if secret not set
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


@webhook_app.post("/webhook/kajabi")
async def handle_kajabi_webhook(
    request: Request,
    x_kajabi_signature: str = Header(None)
):
    """
    Handle Kajabi webhook events.
    
    Expected events:
    - purchase.created: Create a new token for the user
    - purchase.cancelled: Revoke the user's token
    - purchase.refunded: Revoke the user's token
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature if secret is configured
    if KAJABI_WEBHOOK_SECRET and x_kajabi_signature:
        if not verify_kajabi_signature(body, x_kajabi_signature, KAJABI_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    event = payload.get("event", "")
    data = payload.get("data", {})
    
    # Extract user information
    # Adjust these fields based on your Kajabi webhook payload structure
    user_email = data.get("customer", {}).get("email") or data.get("email")
    user_id = data.get("customer", {}).get("id") or data.get("user_id") or user_email
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Could not extract user identifier")
    
    # Handle different events
    if event in ["purchase.created", "order.completed"]:
        # Create a new token for the user
        # First, check if user already has an active token
        tokens = load_tokens()
        existing_token = None
        for token, token_data in tokens.items():
            if (token_data.get("user_id") == str(user_id) and 
                token_data.get("active", True)):
                existing_token = token
                break
        
        if existing_token:
            return {
                "status": "success",
                "message": f"User already has an active token",
                "user_id": user_id
            }
        
        # Create new token (default 30 days, adjust based on subscription)
        expires_days = 30  # You can extract this from the purchase data
        token, expires_at = create_token(str(user_id), expires_days)
        
        return {
            "status": "success",
            "message": "Token created",
            "user_id": user_id,
            "token_preview": token[:16] + "...",
            "expires_at": expires_at
        }
    
    elif event in ["purchase.cancelled", "purchase.refunded", "subscription.cancelled"]:
        # Revoke all tokens for this user
        tokens = load_tokens()
        revoked_count = 0
        
        for token, token_data in tokens.items():
            if token_data.get("user_id") == str(user_id):
                token_data["active"] = False
                revoked_count += 1
        
        if revoked_count > 0:
            from token_manager import save_tokens
            save_tokens(tokens)
        
        return {
            "status": "success",
            "message": f"Revoked {revoked_count} token(s)",
            "user_id": user_id
        }
    
    else:
        return {
            "status": "ignored",
            "message": f"Event '{event}' not handled",
            "user_id": user_id
        }


@webhook_app.get("/webhook/kajabi/test")
async def test_webhook():
    """Test endpoint to verify webhook is accessible"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is active",
        "tokens_count": len(load_tokens())
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEBHOOK_PORT", "8001"))
    uvicorn.run(webhook_app, host="0.0.0.0", port=port)

