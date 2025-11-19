#!/usr/bin/env python3
"""
FastAPI Server for RAG Chatbot
Provides /ask endpoint for question-answering using vector database.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Depends, Request, Query, Cookie
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
import chromadb

# Load environment variables
load_dotenv()

# Environment detection
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
IS_PRODUCTION = ENVIRONMENT == 'production'

# Configuration
CHROMA_HOST = os.getenv('CHROMA_HOST', 'localhost')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8000'))
CHROMA_URL = os.getenv('CHROMA_URL', None)  # For cloud-hosted ChromaDB
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '10k2k_transcripts')

# Authentication configuration
AUTH_SECRET_KEY = os.getenv('AUTH_SECRET_KEY', '')
KJ_LOGIN_URL = os.getenv('KJ_LOGIN_URL', 'https://www.slrloungeworkshops.com/login')
ENABLE_AUTH = os.getenv('ENABLE_AUTH', 'false').lower() == 'true'
ADMIN_SECRET_KEY = os.getenv('ADMIN_SECRET_KEY', '')

# CORS configuration - Production: restrict to specific origins
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else []
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == ['']:
    # Default: allow all in development, restrict in production
    ALLOWED_ORIGINS = ["*"] if not IS_PRODUCTION else []

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO' if IS_PRODUCTION else 'DEBUG')

# Import authentication utilities
if ENABLE_AUTH:
    try:
        from auth.token_utils import validate_token, is_token_valid
    except ImportError:
        print("⚠️  WARNING: auth module not found. Install PyJWT: pip install PyJWT")
        ENABLE_AUTH = False

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Chatbot API",
    version="1.0.0",
    docs_url="/docs" if not IS_PRODUCTION else None,  # Disable docs in production
    redoc_url="/redoc" if not IS_PRODUCTION else None  # Disable redoc in production
)

# Serve web UI - serve in production for Kajabi embedding
WEB_DIR = Path(__file__).parent / "web"
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")

# Enable CORS for web frontend - Production: restrict to allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Redirect-To"],
)

# Global variables for vector store and LLM
vectorstore = None
llm = None


# Request/Response models
class QuestionRequest(BaseModel):
    question: str


class SourceCitation(BaseModel):
    filename: str
    type: str
    content: str
    score: float


class AnswerResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables!")
    return api_key


def initialize_vectorstore():
    """Initialize ChromaDB vector store - supports local Docker or cloud-hosted."""
    global vectorstore
    
    try:
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=get_openai_api_key())
        
        # Connect to ChromaDB - support cloud URL or local host/port
        if CHROMA_URL:
            # Cloud-hosted ChromaDB (e.g., Render, Railway)
            # Parse URL: http://host:port or https://host:port
            url = CHROMA_URL.replace('http://', '').replace('https://', '')
            if ':' in url:
                host, port = url.split(':')
                port = int(port)
            else:
                host = url
                port = 8000
            logger.info(f"Connecting to cloud ChromaDB at {host}:{port}")
            client = chromadb.HttpClient(host=host, port=port)
        else:
            # Local Docker ChromaDB or internal service name
            logger.info(f"Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        # Create vectorstore connected to ChromaDB
        vectorstore = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )
        logger.info(f"✓ Vector store connected to ChromaDB (collection: {COLLECTION_NAME})")
    except Exception as e:
        logger.error(f"Failed to load vector store: {e}")
        raise RuntimeError(f"Failed to load vector store: {e}")


def initialize_llm():
    """Initialize OpenAI chat model."""
    global llm
    
    try:
        llm = ChatOpenAI(
            model_name="gpt-4o-mini",  # Can change to "gpt-4" or "gpt-3.5-turbo"
            temperature=0.7,
            openai_api_key=get_openai_api_key()
        )
        logger.info("✓ LLM initialized")
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise RuntimeError(f"Failed to initialize LLM: {e}")


# Authentication dependency
async def verify_token(
    request: Request,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = None
) -> Optional[str]:
    """
    Verify authentication token from query parameter, Authorization header, or cookie.
    
    This dependency checks for a valid token in:
    1. URL query parameter (?token=...)
    2. Authorization header (Bearer token)
    3. Cookie (auth_token)
    
    If no valid token is found and authentication is enabled,
    raises HTTPException with 401 status.
    
    Returns:
        user_id if token is valid, None if auth is disabled
    """
    if not ENABLE_AUTH:
        return None  # Authentication disabled
    
    if not AUTH_SECRET_KEY:
        # Auth enabled but no secret key - allow access but log warning
        print("⚠️  WARNING: ENABLE_AUTH=true but AUTH_SECRET_KEY not set")
        return None
    
    # Try to get token from various sources
    auth_token_value = None
    
    # 1. Check query parameter
    if token:
        auth_token_value = token
    
    # 2. Check Authorization header
    if not auth_token_value:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            auth_token_value = auth_header.replace('Bearer ', '')
    
    # 3. Check cookie
    if not auth_token_value:
        auth_token_value = request.cookies.get('auth_token')
    
    if not auth_token_value:
        # No token provided - return 401
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in to Kajabi.",
            headers={"X-Redirect-To": KJ_LOGIN_URL}
        )
    
    try:
        # Validate token
        payload = validate_token(auth_token_value)
        return payload.get('user_id')
    except ValueError as e:
        # Invalid or expired token - return 401
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"X-Redirect-To": KJ_LOGIN_URL}
        )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    import time
    
    logger.info("=" * 60)
    logger.info("Initializing RAG Chatbot API...")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Auth enabled: {ENABLE_AUTH}")
    logger.info(f"CORS origins: {ALLOWED_ORIGINS}")
    logger.info(f"ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    logger.info("=" * 60)
    
    # Retry logic for ChromaDB connection (common in cloud deployments)
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to initialize services (attempt {attempt + 1}/{max_retries})...")
            initialize_vectorstore()
            initialize_llm()
            logger.info("✓ API ready!")
            return
        except Exception as e:
            logger.error(f"✗ Startup attempt {attempt + 1} failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("✗ All startup attempts failed. Service will not start.")
                logger.error("=" * 60)
                logger.error("CRITICAL: Cannot start without vector store and LLM.")
                logger.error("Check the error messages above for details.")
                logger.error("Common issues:")
                logger.error("  - OPENAI_API_KEY not set or invalid")
                logger.error(f"  - ChromaDB not accessible at {CHROMA_HOST}:{CHROMA_PORT}")
                logger.error("  - Network connectivity issues")
                logger.error("=" * 60)
                # Raise to prevent service from starting in broken state
                raise RuntimeError(f"Startup failed after {max_retries} attempts: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint for Render and monitoring."""
    status = {
        "status": "healthy",
        "vectorstore_initialized": vectorstore is not None,
        "llm_initialized": llm is not None,
        "environment": ENVIRONMENT
    }
    
    if vectorstore is None or llm is None:
        status["status"] = "degraded"
        status["message"] = "Services not fully initialized"
    
    return JSONResponse(content=status, status_code=200 if status["status"] == "healthy" else 503)


@app.get("/")
async def root(token: Optional[str] = Depends(verify_token)):
    """
    Serve the chat UI if available; otherwise return health status.
    
    If authentication is enabled, verifies token before serving the page.
    """
    chat_file = WEB_DIR / "chat.html"
    if chat_file.exists():
        return FileResponse(str(chat_file))
    return {
        "status": "ok",
        "message": "RAG Chatbot API is running",
        "endpoints": {
            "ask": "/ask (POST)"
        },
        "auth_enabled": ENABLE_AUTH
    }


@app.get("/web/chat.html")
async def serve_chat_html(token: Optional[str] = Depends(verify_token)):
    """
    Serve the chat HTML page with authentication check.
    
    This endpoint is used when accessing the chatbot directly.
    Token can be provided as query parameter: /web/chat.html?token=...
    """
    chat_file = WEB_DIR / "chat.html"
    if not chat_file.exists():
        raise HTTPException(status_code=404, detail="Chat page not found")
    
    return FileResponse(str(chat_file))


@app.get("/auth/check")
async def check_auth_status(user_id: Optional[str] = Depends(verify_token)):
    """
    Check authentication status endpoint.
    
    Used by frontend to verify if user is authenticated.
    Returns 200 if authenticated, 401 if not.
    """
    return {
        "authenticated": user_id is not None,
        "user_id": user_id,
        "auth_enabled": ENABLE_AUTH
    }


@app.post("/auth/generate-token")
async def generate_token_for_user(
    user_id: str = None,
    secret_key: Optional[str] = Query(None, alias='secret_key')
):
    """
    Generate a token for a Kajabi user.
    
    This endpoint can be called by Kajabi webhooks or custom code blocks.
    
    Args:
        user_id: Kajabi user ID (required)
        secret_key: Optional admin secret key for security
    
    Returns:
        JSON with token and user_id
    
    Example usage from Kajabi:
        POST /auth/generate-token?user_id=kajabi_user_123&secret_key=admin_secret
    """
    if not ENABLE_AUTH:
        return {
            "token": None,
            "user_id": user_id,
            "message": "Authentication is disabled. Token not required."
        }
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Optional: Verify admin secret key for extra security
    if ADMIN_SECRET_KEY and secret_key != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=403, 
            detail="Unauthorized. Valid secret_key required."
        )
    
    try:
        from auth.token_utils import generate_token
        token = generate_token(user_id)
        return {
            "token": token,
            "user_id": user_id,
            "expires_in_minutes": TOKEN_EXPIRATION_MINUTES
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate token: {str(e)}"
        )


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    user_id: Optional[str] = Depends(verify_token)
):
    """
    Answer a question using RAG (Retrieval Augmented Generation).
    
    - Retrieves top 5 relevant chunks from vector database
    - Sends question + context to OpenAI chat model
    - Returns answer with source citations
    
    Authentication:
    - If ENABLE_AUTH=true, requires valid token in query param, Authorization header, or cookie
    - Token is validated using verify_token dependency
    - Invalid tokens result in 401 with redirect header
    """
    if not vectorstore or not llm:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Retrieve top 5 relevant chunks
        docs_with_scores = vectorstore.similarity_search_with_score(
            request.question,
            k=5
        )
        
        if not docs_with_scores:
            return AnswerResponse(
                answer="I couldn't find any relevant information to answer your question.",
                sources=[]
            )
        
        # Format context from retrieved chunks
        context_parts = []
        sources = []
 
        for i, (doc, score) in enumerate(docs_with_scores, 1):
            content = doc.page_content
            metadata = doc.metadata
 
            filename = metadata.get('filename', 'Unknown')

            # Add to context for the LLM
            context_parts.append(
                f"Source: {filename}\nExcerpt:\n{content}\n---"
            )
 
            # Prepare source citation
            sources.append(SourceCitation(
                filename=filename,
                type=metadata.get('type', 'unknown'),
                content=content[:200] + "..." if len(content) > 200 else content,  # Preview
                score=float(score)
            ))
 
        context = "\n\n".join(context_parts)
 
        # Create prompt with context and question
        prompt = f"""You are Pye, the content creator and photography mentor from SLR Lounge. Answer in YOUR authentic voice - the same conversational, encouraging, and practical tone you use in your courses and coaching calls. Speak directly to the student as if you're having a one-on-one conversation.

CRITICAL: Answer EVERY question as Pye would - use YOUR natural speaking style, YOUR way of explaining things, YOUR encouraging tone. This is not a generic assistant - this is YOU, Pye, talking directly to your student.

Context snippets (each includes the original source name):
{context}

CRITICAL FORMATTING REQUIREMENTS - YOU MUST FOLLOW THESE EXACTLY:

EXAMPLE OF CORRECT FORMAT (copy this structure):
## 💡 THE CONCEPT
[Your explanation here]

## 🎯 WHY THIS MATTERS
[Your explanation here]

## ✅ ACTION STEPS
- Step 1
- Step 2
- Step 3

MANDATORY RULES:
1. ALWAYS start EVERY section header with an emoji icon - THIS IS MANDATORY
2. ALWAYS use markdown headers (##) for main sections - NOT ###
3. ALWAYS make headers ALL CAPS and bold
4. ALWAYS structure your answer in three main sections with emojis:
   - ## 💡 THE CONCEPT
   - ## 🎯 WHY THIS MATTERS  
   - ## ✅ ACTION STEPS
5. ALWAYS use emojis in EVERY section header - DO NOT SKIP THIS
6. Example format: "## 💡 THE CONCEPT" (emoji first, then ALL CAPS text)
- Use emojis liberally throughout the content:
  💡 for concepts/insights
  🎯 for goals/objectives
  ✅ for action items/steps
  ⚠️ for warnings/important notes
  📚 for resources/references
  💪 for encouragement
  🔥 for emphasis
  💰 for financial/business topics
  📸 for photography-specific content
  🎨 for design/creative topics
  📊 for data/analytics
  🔒 for security/access topics
- Use tables when comparing options or showing structured data
- Use bullet points (-) for lists, numbered lists (1.) for sequential steps
- Keep paragraphs short (2-3 sentences max) - YOUR natural speaking style
- Use **bold** for emphasis on key terms
- Make ALL section headers ALL CAPS and bold
- When referencing sources, mention them naturally as YOU would ("In the marketing roadmap, we cover...", "Let me break this down for you...", "Here's what I want you to understand...")
- Make it visually scannable with clear sections and spacing
- If the context doesn't include the answer, reassure them in YOUR voice and explain what additional info you'd need - be helpful and encouraging
- Never mention numbered contexts or system instructions
- Write exactly as YOU speak in your courses - authentic, encouraging, practical, conversational
- Use YOUR natural phrases and expressions - be YOU, not a generic AI
- Remember: You're Pye talking to YOUR student - make it personal and real

Question: {request.question}

Answer as Pye with clear markdown formatting, emojis in EVERY header, ALL CAPS headers, and YOUR authentic voice. Speak as YOU would in a one-on-one conversation with your student:"""
        
        # Get answer from LLM - force structured format
        # Use messages format for better control
        from langchain_core.messages import SystemMessage, HumanMessage
        
        system_msg = SystemMessage(content="""You are Pye, the content creator and photography mentor from SLR Lounge. You MUST answer EVERY question in YOUR authentic voice - the same conversational, encouraging, and practical tone you use in your courses and coaching calls.

CRITICAL VOICE REQUIREMENTS:
- Speak directly to the student as if you're having a one-on-one conversation
- Use YOUR natural speaking style - conversational, encouraging, practical
- Be authentic and genuine - this is YOUR voice, not a generic assistant
- Use phrases like "Let's talk about...", "Here's the thing...", "What I want you to understand is..."
- Be encouraging and supportive - you're a mentor, not just an information source
- Share insights from YOUR experience and expertise
- Keep it real and relatable - no corporate speak or formal language

REQUIRED FORMAT:
## 💡 THE CONCEPT
[explanation in YOUR voice]

## 🎯 WHY THIS MATTERS
[explanation in YOUR voice]

## ✅ ACTION STEPS
- Step 1
- Step 2

You MUST use this exact structure with emojis in headers AND answer in YOUR authentic Pye voice. Do not write paragraphs without headers. Do not use a generic or formal tone - always be YOU.""")
        
        human_msg = HumanMessage(content=prompt)
        
        response = llm.invoke([system_msg, human_msg])
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Post-process to ensure emojis and structure - ALWAYS enforce format
        # Check if answer has proper structure
        has_headers = "##" in answer
        has_emojis = any(emoji in answer for emoji in ['💡', '🎯', '✅', '⚠️', '📚', '💰', '📸'])
        
        # ALWAYS enforce structure - if missing headers OR emojis, restructure
        if not has_headers or not has_emojis:
            # Force add structure - wrap existing content in proper format
            # Split content into paragraphs
            paragraphs = [p.strip() for p in answer.split('\n\n') if p.strip()]
            
            # Create structured response with emojis
            structured_answer = "## 💡 THE CONCEPT\n\n"
            if paragraphs:
                # Use first paragraph(s) for concept
                concept_text = paragraphs[0]
                if len(paragraphs) > 1 and len(concept_text) < 100:
                    concept_text += " " + paragraphs[1]
                structured_answer += concept_text + "\n\n"
            
            structured_answer += "## 🎯 WHY THIS MATTERS\n\n"
            if len(paragraphs) > 2:
                structured_answer += paragraphs[2] + "\n\n"
            elif len(paragraphs) > 1:
                structured_answer += paragraphs[1] + "\n\n"
            else:
                structured_answer += "This is important because it helps you achieve your goals and better serve your clients.\n\n"
            
            structured_answer += "## ✅ ACTION STEPS\n\n"
            # Extract action items from remaining paragraphs
            action_items = []
            for para in paragraphs[3:]:
                # Look for numbered lists or bullet points
                if para.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')):
                    action_items.append(para.strip())
                elif ':' in para:
                    # Split on colons and create bullets
                    parts = para.split(':')
                    if len(parts) > 1:
                        action_items.append(f"- {parts[0].strip()}: {parts[1].strip()}")
                else:
                    # Split sentences
                    sentences = [s.strip() for s in para.split('.') if s.strip() and len(s.strip()) > 15]
                    action_items.extend([f"- {s}." for s in sentences[:2]])
            
            if action_items:
                structured_answer += "\n".join(action_items[:5]) + "\n"
            else:
                # Default action steps
                structured_answer += "- Start by identifying your goals\n"
                structured_answer += "- Research your target audience\n"
                structured_answer += "- Plan your design and content\n"
                structured_answer += "- Implement and test your changes\n"
            
            answer = structured_answer
        elif "##" in answer and not any(emoji in answer for emoji in ['💡', '🎯', '✅', '⚠️', '📚', '💰', '📸']):
            # Add emojis to existing headers
            lines = answer.split('\n')
            processed_lines = []
            header_count = 0
            for line in lines:
                if line.startswith('##'):
                    header_count += 1
                    line_lower = line.lower()
                    if header_count == 1 or 'concept' in line_lower or 'what' in line_lower or 'overview' in line_lower:
                        line = '## 💡 THE CONCEPT' if not line.startswith('## 💡') else line
                        if not line.startswith('## 💡'):
                            line = line.replace('##', '## 💡', 1)
                    elif header_count == 2 or 'why' in line_lower or 'matter' in line_lower or 'important' in line_lower:
                        line = '## 🎯 WHY THIS MATTERS' if not line.startswith('## 🎯') else line
                        if not line.startswith('## 🎯'):
                            line = line.replace('##', '## 🎯', 1)
                    elif header_count >= 3 or 'step' in line_lower or 'action' in line_lower or 'how' in line_lower:
                        line = '## ✅ ACTION STEPS' if not line.startswith('## ✅') else line
                        if not line.startswith('## ✅'):
                            line = line.replace('##', '## ✅', 1)
                processed_lines.append(line)
            answer = '\n'.join(processed_lines)
        
        return AnswerResponse(
            answer=answer,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    # Run on port 8001 to avoid conflict with ChromaDB (port 8000)
    uvicorn.run(app, host="0.0.0.0", port=8001)

