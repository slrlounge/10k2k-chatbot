"""
FastAPI Backend for RAG Chatbot with Gemini FileSearch
Includes token authentication for Kajabi paywall integration
"""
import os
import secrets
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google.genai import Client
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="RAG Chatbot API", version="1.0.0")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this to your Kajabi domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
try:
    gemini_client = Client()
except Exception as e:
    print(f"Warning: Could not initialize Gemini client: {e}")
    gemini_client = None

# Configuration from environment variables
GEMINI_STORE_ID = os.getenv("GEMINI_STORE_ID", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))

# Token storage (loads from file if exists, otherwise uses in-memory)
# Format: {token: {"user_id": str, "created_at": str, "active": bool, "expires_at": str}}
TOKEN_FILE = Path("tokens.json")

def load_tokens_from_file():
    """Load tokens from JSON file if it exists"""
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load tokens from file: {e}")
    return {}

TOKEN_DB: dict[str, dict] = load_tokens_from_file()

# Chat history storage
# Format: {user_id: [{"id": str, "title": str, "created_at": str, "messages": List[ChatMessage]}]}
CHAT_HISTORY_FILE = Path("chat_history.json")

def load_chat_history():
    """Load chat history from JSON file if it exists"""
    if CHAT_HISTORY_FILE.exists():
        try:
            with open(CHAT_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load chat history from file: {e}")
    return {}

def save_chat_history():
    """Save chat history to file"""
    try:
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump(CHAT_HISTORY_DB, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save chat history to file: {e}")

CHAT_HISTORY_DB: dict[str, list] = load_chat_history()


# Pydantic models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[dict]] = []


class TokenCreate(BaseModel):
    user_id: str
    expires_in_days: Optional[int] = 30


class TokenResponse(BaseModel):
    token: str
    expires_at: Optional[str] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[ChatMessage]


# Authentication dependency
async def verify_token(authorization: Optional[str] = Header(None)):
    """Verify the bearer token from the Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    if token not in TOKEN_DB:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    token_data = TOKEN_DB[token]
    if not token_data.get("active", True):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    return token_data


# API Routes
@app.get("/chat", response_class=HTMLResponse)
async def chat_ui():
    """Serve the new chatbot UI with chat history sidebar"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SLR Lounge Chatbot</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: white;
                height: 100vh;
                overflow: hidden;
            }
            .app-container {
                display: flex;
                height: 100vh;
                width: 100%;
            }
            /* Left Sidebar */
            .sidebar {
                width: 280px;
                background: white;
                border-right: 1px solid #e5e5e5;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            .sidebar-header {
                padding: 16px;
                border-bottom: 1px solid #e5e5e5;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .sidebar-header h2 {
                font-size: 16px;
                font-weight: 600;
                color: #333;
            }
            .sidebar-close {
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                color: #666;
                padding: 4px;
            }
            .sidebar-search {
                padding: 12px 16px;
                border-bottom: 1px solid #e5e5e5;
            }
            .sidebar-search input {
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                outline: none;
            }
            .sidebar-search input:focus {
                border-color: #d4a574;
            }
            .conversation-list {
                flex: 1;
                overflow-y: auto;
                padding: 8px 0;
            }
            .conversation-item {
                padding: 12px 16px;
                cursor: pointer;
                transition: background 0.2s;
                border-left: 3px solid transparent;
            }
            .conversation-item:hover {
                background: #f5f5f5;
            }
            .conversation-item.active {
                background: #f5ebe0;
                border-left-color: #d4a574;
            }
            .conversation-title {
                font-weight: 600;
                font-size: 14px;
                color: #333;
                margin-bottom: 4px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .conversation-time {
                font-size: 12px;
                color: #999;
            }
            /* Main Chat Area */
            .main-chat {
                flex: 1;
                display: flex;
                flex-direction: column;
                background: white;
            }
            .chat-header {
                padding: 16px 24px;
                border-bottom: 1px solid #e5e5e5;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .chat-header h1 {
                font-size: 18px;
                font-weight: 600;
                color: #333;
            }
            .new-chat-button {
                background: #d4a574;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.2s;
            }
            .new-chat-button:hover {
                background: #c49564;
            }
            .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 24px;
                background: white;
            }
            .welcome-message {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                text-align: center;
            }
            .welcome-message h2 {
                font-size: 24px;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }
            .welcome-message p {
                font-size: 16px;
                color: #666;
            }
            .message {
                margin-bottom: 16px;
                display: flex;
                flex-direction: column;
            }
            .message.user {
                align-items: flex-end;
            }
            .message.assistant {
                align-items: flex-start;
            }
            .message-bubble {
                max-width: 70%;
                padding: 12px 16px;
                border-radius: 8px;
                word-wrap: break-word;
                line-height: 1.5;
                font-size: 14px;
            }
            .message.user .message-bubble {
                background: #e0e0e0;
                color: #333;
            }
            .message.assistant .message-bubble {
                background: #f5f5f5;
                color: #333;
            }
            .chat-input-container {
                padding: 16px 24px;
                border-top: 1px solid #e5e5e5;
                background: white;
            }
            .chat-input-form {
                display: flex;
                gap: 12px;
                align-items: center;
            }
            #messageInput {
                flex: 1;
                padding: 12px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                outline: none;
                background: #f9f9f9;
            }
            #messageInput:focus {
                border-color: #d4a574;
                background: white;
            }
            #sendButton {
                background: #d4a574;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 8px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            }
            #sendButton:hover {
                background: #c49564;
            }
            #sendButton:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .send-icon {
                width: 20px;
                height: 20px;
                color: white;
            }
            .loading {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #d4a574;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .empty-state {
                text-align: center;
                color: #999;
                padding: 40px;
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- Left Sidebar -->
            <div class="sidebar">
                <div class="sidebar-header">
                    <h2>Chat History</h2>
                    <button class="sidebar-close" id="sidebarClose">×</button>
                </div>
                <div class="sidebar-search">
                    <input type="text" id="searchInput" placeholder="Search chats..." />
                </div>
                <div class="conversation-list" id="conversationList">
                    <!-- Conversations will be loaded here -->
                </div>
            </div>
            
            <!-- Main Chat Area -->
            <div class="main-chat">
                <div class="chat-header">
                    <h1>SLR Lounge Chatbot</h1>
                    <button class="new-chat-button" id="newChatButton">+ New Chat</button>
                </div>
                <div class="chat-messages" id="chatMessages">
                    <div class="welcome-message">
                        <h2>Welcome to SLR Lounge Chatbot</h2>
                        <p>Ask me anything about the 10K for 2K mentorship program!</p>
                    </div>
                </div>
                <div class="chat-input-container">
                    <form class="chat-input-form" id="chatForm">
                        <input type="text" id="messageInput" placeholder="Ask a question about the 10K for 2K mentorship..." />
                        <button type="submit" id="sendButton">
                            <svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </form>
                </div>
            </div>
        </div>
        <script>
            const API_BASE = window.location.origin;
            let authToken = null;
            let currentConversationId = null;
            let conversations = [];
            const TOKEN_STORAGE_KEY = 'chatbot_auth_token';

            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const chatForm = document.getElementById('chatForm');
            const chatMessages = document.getElementById('chatMessages');
            const newChatButton = document.getElementById('newChatButton');
            const conversationList = document.getElementById('conversationList');
            const searchInput = document.getElementById('searchInput');
            const sidebarClose = document.getElementById('sidebarClose');

            // Get auth token
            function getAuthToken() {
                const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
                if (storedToken) return storedToken;
                const urlParams = new URLSearchParams(window.location.search);
                const tokenParam = urlParams.get('token');
                if (tokenParam) {
                    localStorage.setItem(TOKEN_STORAGE_KEY, tokenParam);
                    return tokenParam;
                }
                return null;
            }

            // Format date for display (matches design: "Dec 8, 10:03 PM")
            function formatDate(dateStr) {
                try {
                    // If it's a timestamp string, try to parse it
                    let date;
                    if (typeof dateStr === 'string' && dateStr.length > 10) {
                        // Try parsing as ISO or use current time as fallback
                        date = new Date(dateStr);
                        if (isNaN(date.getTime())) {
                            date = new Date();
                        }
                    } else {
                        date = new Date();
                    }
                    
                    return date.toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric', 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true
                    });
                } catch {
                    return new Date().toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric', 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true
                    });
                }
            }

            // Load conversations
            async function loadConversations(searchQuery = '') {
                try {
                    const url = searchQuery 
                        ? `${API_BASE}/api/conversations?search=${encodeURIComponent(searchQuery)}`
                        : `${API_BASE}/api/conversations`;
                    const response = await fetch(url, {
                        headers: {
                            'Authorization': `Bearer ${authToken}`
                        }
                    });
                    if (!response.ok) throw new Error('Failed to load conversations');
                    const data = await response.json();
                    conversations = data.conversations;
                    renderConversations();
                } catch (error) {
                    console.error('Error loading conversations:', error);
                }
            }

            // Render conversations list
            function renderConversations() {
                conversationList.innerHTML = '';
                if (conversations.length === 0) {
                    conversationList.innerHTML = '<div class="empty-state">No conversations yet</div>';
                    return;
                }
                conversations.forEach(conv => {
                    const item = document.createElement('div');
                    item.className = 'conversation-item';
                    if (conv.id === currentConversationId) {
                        item.classList.add('active');
                    }
                    item.innerHTML = `
                        <div class="conversation-title">${escapeHtml(conv.title)}</div>
                        <div class="conversation-time">${formatDate(conv.updated_at)}</div>
                    `;
                    item.addEventListener('click', () => loadConversation(conv.id));
                    conversationList.appendChild(item);
                });
            }

            // Create new conversation
            async function createNewConversation() {
                try {
                    const response = await fetch(`${API_BASE}/api/conversations`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify({ title: 'New Chat' })
                    });
                    if (!response.ok) throw new Error('Failed to create conversation');
                    const data = await response.json();
                    currentConversationId = data.id;
                    await loadConversations(searchInput.value);
                    clearChatMessages();
                    showWelcomeMessage();
                } catch (error) {
                    console.error('Error creating conversation:', error);
                    alert('Failed to create new conversation');
                }
            }

            // Load conversation
            async function loadConversation(conversationId) {
                try {
                    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
                        headers: {
                            'Authorization': `Bearer ${authToken}`
                        }
                    });
                    if (!response.ok) throw new Error('Failed to load conversation');
                    const data = await response.json();
                    currentConversationId = conversationId;
                    clearChatMessages();
                    hideWelcomeMessage();
                    data.messages.forEach(msg => {
                        addMessageToUI(msg.role, msg.content);
                    });
                    renderConversations();
                } catch (error) {
                    console.error('Error loading conversation:', error);
                    alert('Failed to load conversation');
                }
            }

            // Clear chat messages
            function clearChatMessages() {
                chatMessages.innerHTML = '';
            }

            // Show welcome message
            function showWelcomeMessage() {
                chatMessages.innerHTML = `
                    <div class="welcome-message">
                        <h2>Welcome to SLR Lounge Chatbot</h2>
                        <p>Ask me anything about the 10K for 2K mentorship program!</p>
                    </div>
                `;
            }

            // Hide welcome message
            function hideWelcomeMessage() {
                const welcome = chatMessages.querySelector('.welcome-message');
                if (welcome) welcome.remove();
            }

            // Send message
            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const message = messageInput.value.trim();
                if (!message) return;

                if (!authToken) {
                    alert('Please provide an access token to start chatting.');
                    return;
                }

                // Create conversation if none exists
                if (!currentConversationId) {
                    await createNewConversation();
                }

                addMessageToUI('user', message);
                messageInput.value = '';
                sendButton.disabled = true;
                sendButton.innerHTML = '<div class="loading"></div>';

                try {
                    // Get current conversation history
                    let conversationHistory = [];
                    if (currentConversationId) {
                        const convResponse = await fetch(`${API_BASE}/api/conversations/${currentConversationId}`, {
                            headers: { 'Authorization': `Bearer ${authToken}` }
                        });
                        if (convResponse.ok) {
                            const convData = await convResponse.json();
                            conversationHistory = convData.messages.map(msg => ({
                                role: msg.role,
                                content: msg.content
                            }));
                        }
                    }

                    const response = await fetch(`${API_BASE}/api/chat`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify({
                            message: message,
                            conversation_history: conversationHistory,
                            conversation_id: currentConversationId
                        })
                    });

                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get response');
                    }

                    const data = await response.json();
                    addMessageToUI('assistant', data.response);
                    hideWelcomeMessage();
                    
                    // Reload conversations to update list
                    await loadConversations(searchInput.value);
                } catch (error) {
                    addMessageToUI('assistant', `Error: ${error.message}`, true);
                } finally {
                    sendButton.disabled = false;
                    sendButton.innerHTML = '<svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
                }
            });

            function addMessageToUI(role, content, isError = false) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;
                if (isError) messageDiv.style.color = '#e74c3c';
                
                const bubble = document.createElement('div');
                bubble.className = 'message-bubble';
                bubble.innerHTML = escapeHtml(content).replace(/\\n/g, '<br>');
                messageDiv.appendChild(bubble);
                
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            // Event listeners
            newChatButton.addEventListener('click', createNewConversation);
            searchInput.addEventListener('input', (e) => {
                loadConversations(e.target.value);
            });
            sidebarClose.addEventListener('click', () => {
                document.querySelector('.sidebar').style.display = 'none';
            });

            // Initialize
            authToken = getAuthToken();
            if (authToken) {
                loadConversations();
            } else {
                alert('Please provide an access token to use the chatbot.');
            }
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/embed", response_class=HTMLResponse)
async def embed_ui():
    """Embeddable chatbot UI for Kajabi - matches the design exactly"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SLR Lounge Chatbot</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            html, body {
                height: 100%;
                overflow: hidden;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: white;
            }
            .app-container {
                display: flex;
                height: 100vh;
                width: 100%;
            }
            /* Left Sidebar */
            .sidebar {
                width: 280px;
                background: white;
                border-right: 1px solid #e5e5e5;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            .sidebar-header {
                padding: 16px;
                border-bottom: 1px solid #e5e5e5;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .sidebar-header h2 {
                font-size: 16px;
                font-weight: 600;
                color: #333;
            }
            .sidebar-close {
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                color: #666;
                padding: 4px;
            }
            .sidebar-search {
                padding: 12px 16px;
                border-bottom: 1px solid #e5e5e5;
            }
            .sidebar-search input {
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                outline: none;
            }
            .sidebar-search input:focus {
                border-color: #d4a574;
            }
            .conversation-list {
                flex: 1;
                overflow-y: auto;
                padding: 8px 0;
            }
            .conversation-item {
                padding: 12px 16px;
                cursor: pointer;
                transition: background 0.2s;
                border-left: 3px solid transparent;
            }
            .conversation-item:hover {
                background: #f5f5f5;
            }
            .conversation-item.active {
                background: #f5ebe0;
                border-left-color: #d4a574;
            }
            .conversation-title {
                font-weight: 600;
                font-size: 14px;
                color: #333;
                margin-bottom: 4px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .conversation-time {
                font-size: 12px;
                color: #999;
            }
            /* Main Chat Area */
            .main-chat {
                flex: 1;
                display: flex;
                flex-direction: column;
                background: white;
            }
            .chat-header {
                padding: 16px 24px;
                border-bottom: 1px solid #e5e5e5;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .chat-header h1 {
                font-size: 18px;
                font-weight: 600;
                color: #333;
            }
            .new-chat-button {
                background: #d4a574;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.2s;
            }
            .new-chat-button:hover {
                background: #c49564;
            }
            .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 24px;
                background: white;
            }
            .welcome-message {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                text-align: center;
            }
            .welcome-message h2 {
                font-size: 24px;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }
            .welcome-message p {
                font-size: 16px;
                color: #666;
            }
            .message {
                margin-bottom: 16px;
                display: flex;
                flex-direction: column;
            }
            .message.user {
                align-items: flex-end;
            }
            .message.assistant {
                align-items: flex-start;
            }
            .message-bubble {
                max-width: 70%;
                padding: 12px 16px;
                border-radius: 8px;
                word-wrap: break-word;
                line-height: 1.5;
                font-size: 14px;
            }
            .message.user .message-bubble {
                background: #e0e0e0;
                color: #333;
            }
            .message.assistant .message-bubble {
                background: #f5f5f5;
                color: #333;
            }
            .chat-input-container {
                padding: 16px 24px;
                border-top: 1px solid #e5e5e5;
                background: white;
            }
            .chat-input-form {
                display: flex;
                gap: 12px;
                align-items: center;
            }
            #messageInput {
                flex: 1;
                padding: 12px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                outline: none;
                background: #f9f9f9;
            }
            #messageInput:focus {
                border-color: #d4a574;
                background: white;
            }
            #sendButton {
                background: #d4a574;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 8px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            }
            #sendButton:hover {
                background: #c49564;
            }
            #sendButton:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .send-icon {
                width: 20px;
                height: 20px;
                color: white;
            }
            .loading {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #d4a574;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .empty-state {
                text-align: center;
                color: #999;
                padding: 40px;
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- Left Sidebar -->
            <div class="sidebar">
                <div class="sidebar-header">
                    <h2>Chat History</h2>
                    <button class="sidebar-close" id="sidebarClose">×</button>
                </div>
                <div class="sidebar-search">
                    <input type="text" id="searchInput" placeholder="Search chats..." />
                </div>
                <div class="conversation-list" id="conversationList">
                    <!-- Conversations will be loaded here -->
                </div>
            </div>
            
            <!-- Main Chat Area -->
            <div class="main-chat">
                <div class="chat-header">
                    <h1>SLR Lounge Chatbot</h1>
                    <button class="new-chat-button" id="newChatButton">+ New Chat</button>
                </div>
                <div class="chat-messages" id="chatMessages">
                    <div class="welcome-message">
                        <h2>Welcome to SLR Lounge Chatbot</h2>
                        <p>Ask me anything about the 10K for 2K mentorship program!</p>
                    </div>
                </div>
                <div class="chat-input-container">
                    <form class="chat-input-form" id="chatForm">
                        <input type="text" id="messageInput" placeholder="Ask a question about the 10K for 2K mentorship..." />
                        <button type="submit" id="sendButton">
                            <svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </form>
                </div>
            </div>
        </div>
        <script>
            // Get API base URL - use origin, removing /embed if present
            const API_BASE = (() => {
                const origin = window.location.origin;
                const pathname = window.location.pathname;
                // If we're on /embed, remove it from the base
                if (pathname.includes('/embed')) {
                    return origin;
                }
                return origin;
            })();
            let authToken = null;
            let currentConversationId = null;
            let conversations = [];
            const TOKEN_STORAGE_KEY = 'chatbot_auth_token';

            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const chatForm = document.getElementById('chatForm');
            const chatMessages = document.getElementById('chatMessages');
            const newChatButton = document.getElementById('newChatButton');
            const conversationList = document.getElementById('conversationList');
            const searchInput = document.getElementById('searchInput');
            const sidebarClose = document.getElementById('sidebarClose');

            // Get auth token from URL or localStorage
            function getAuthToken() {
                const urlParams = new URLSearchParams(window.location.search);
                const tokenParam = urlParams.get('token');
                if (tokenParam) {
                    localStorage.setItem(TOKEN_STORAGE_KEY, tokenParam);
                    return tokenParam;
                }
                const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
                return storedToken;
            }

            // Format date for display (matches design: "Dec 8, 10:03 PM")
            function formatDate(dateStr) {
                try {
                    let date = new Date(dateStr);
                    if (isNaN(date.getTime())) {
                        date = new Date();
                    }
                    return date.toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric', 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true
                    });
                } catch {
                    return new Date().toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric', 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true
                    });
                }
            }

            // Load conversations
            async function loadConversations(searchQuery = '') {
                try {
                    const url = searchQuery 
                        ? `${API_BASE}/api/conversations?search=${encodeURIComponent(searchQuery)}`
                        : `${API_BASE}/api/conversations`;
                    const response = await fetch(url, {
                        headers: {
                            'Authorization': `Bearer ${authToken}`
                        }
                    });
                    if (!response.ok) throw new Error('Failed to load conversations');
                    const data = await response.json();
                    conversations = data.conversations;
                    renderConversations();
                } catch (error) {
                    console.error('Error loading conversations:', error);
                }
            }

            // Render conversations list
            function renderConversations() {
                conversationList.innerHTML = '';
                if (conversations.length === 0) {
                    conversationList.innerHTML = '<div class="empty-state">No conversations yet</div>';
                    return;
                }
                conversations.forEach(conv => {
                    const item = document.createElement('div');
                    item.className = 'conversation-item';
                    if (conv.id === currentConversationId) {
                        item.classList.add('active');
                    }
                    item.innerHTML = `
                        <div class="conversation-title">${escapeHtml(conv.title)}</div>
                        <div class="conversation-time">${formatDate(conv.updated_at)}</div>
                    `;
                    item.addEventListener('click', () => loadConversation(conv.id));
                    conversationList.appendChild(item);
                });
            }

            // Create new conversation
            async function createNewConversation() {
                try {
                    const response = await fetch(`${API_BASE}/api/conversations`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify({ title: 'New Chat' })
                    });
                    if (!response.ok) throw new Error('Failed to create conversation');
                    const data = await response.json();
                    currentConversationId = data.id;
                    await loadConversations(searchInput.value);
                    clearChatMessages();
                    showWelcomeMessage();
                } catch (error) {
                    console.error('Error creating conversation:', error);
                    alert('Failed to create new conversation');
                }
            }

            // Load conversation
            async function loadConversation(conversationId) {
                try {
                    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
                        headers: {
                            'Authorization': `Bearer ${authToken}`
                        }
                    });
                    if (!response.ok) throw new Error('Failed to load conversation');
                    const data = await response.json();
                    currentConversationId = conversationId;
                    clearChatMessages();
                    hideWelcomeMessage();
                    data.messages.forEach(msg => {
                        addMessageToUI(msg.role, msg.content);
                    });
                    renderConversations();
                } catch (error) {
                    console.error('Error loading conversation:', error);
                    alert('Failed to load conversation');
                }
            }

            // Clear chat messages
            function clearChatMessages() {
                chatMessages.innerHTML = '';
            }

            // Show welcome message
            function showWelcomeMessage() {
                chatMessages.innerHTML = `
                    <div class="welcome-message">
                        <h2>Welcome to SLR Lounge Chatbot</h2>
                        <p>Ask me anything about the 10K for 2K mentorship program!</p>
                    </div>
                `;
            }

            // Hide welcome message
            function hideWelcomeMessage() {
                const welcome = chatMessages.querySelector('.welcome-message');
                if (welcome) welcome.remove();
            }

            // Send message
            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const message = messageInput.value.trim();
                if (!message) return;

                if (!authToken) {
                    alert('Please provide an access token to start chatting.');
                    return;
                }

                // Create conversation if none exists
                if (!currentConversationId) {
                    await createNewConversation();
                }

                addMessageToUI('user', message);
                messageInput.value = '';
                sendButton.disabled = true;
                sendButton.innerHTML = '<div class="loading"></div>';

                try {
                    // Get current conversation history
                    let conversationHistory = [];
                    if (currentConversationId) {
                        const convResponse = await fetch(`${API_BASE}/api/conversations/${currentConversationId}`, {
                            headers: { 'Authorization': `Bearer ${authToken}` }
                        });
                        if (convResponse.ok) {
                            const convData = await convResponse.json();
                            conversationHistory = convData.messages.map(msg => ({
                                role: msg.role,
                                content: msg.content
                            }));
                        }
                    }

                    const response = await fetch(`${API_BASE}/api/chat`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify({
                            message: message,
                            conversation_history: conversationHistory,
                            conversation_id: currentConversationId
                        })
                    });

                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get response');
                    }

                    const data = await response.json();
                    addMessageToUI('assistant', data.response);
                    hideWelcomeMessage();
                    
                    // Reload conversations to update list
                    await loadConversations(searchInput.value);
                } catch (error) {
                    addMessageToUI('assistant', `Error: ${error.message}`, true);
                } finally {
                    sendButton.disabled = false;
                    sendButton.innerHTML = '<svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
                }
            });

            function addMessageToUI(role, content, isError = false) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;
                if (isError) messageDiv.style.color = '#e74c3c';
                
                const bubble = document.createElement('div');
                bubble.className = 'message-bubble';
                bubble.innerHTML = escapeHtml(content).replace(/\\n/g, '<br>');
                messageDiv.appendChild(bubble);
                
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            // Event listeners
            newChatButton.addEventListener('click', createNewConversation);
            searchInput.addEventListener('input', (e) => {
                loadConversations(e.target.value);
            });
            sidebarClose.addEventListener('click', () => {
                document.querySelector('.sidebar').style.display = 'none';
            });

            // Initialize
            authToken = getAuthToken();
            if (authToken) {
                loadConversations();
            } else {
                // Try to get token from parent window (Kajabi integration)
                if (window.parent && window.parent !== window) {
                    window.addEventListener('message', (event) => {
                        if (event.data && event.data.token) {
                            authToken = event.data.token;
                            localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
                            loadConversations();
                        }
                    });
                    // Request token from parent
                    window.parent.postMessage({ type: 'request_token' }, '*');
                } else {
                    alert('Please provide an access token to use the chatbot.');
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the chatbot frontend"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>10K/2K AI Mentor Chatbot</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: #f5f5f5;
            }
            .chat-container {
                width: 100%;
                max-width: 100%;
                background: #f0f0f0;
                border-radius: 8px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .chat-header {
                background: #4285f4;
                color: white;
                padding: 12px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-weight: 500;
            }
            .chat-header .chat-title {
                font-size: 16px;
            }
            .chat-header .wave-button {
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                background: #f0f0f0;
                min-height: 400px;
                max-height: 600px;
            }
            .message {
                margin-bottom: 16px;
                display: flex;
                flex-direction: column;
            }
            .message.user {
                align-items: flex-end;
            }
            .message.assistant {
                align-items: flex-start;
            }
            .message-bubble {
                max-width: 75%;
                padding: 12px 16px;
                border-radius: 8px;
                word-wrap: break-word;
                line-height: 1.5;
                font-size: 14px;
            }
            .message.user .message-bubble {
                background: #e0e0e0;
                color: #333;
            }
            .message.assistant .message-bubble {
                background: #e8e8e8;
                color: #333;
            }
            .chat-input-container {
                padding: 12px 16px;
                background: white;
                border-top: 1px solid #e0e0e0;
            }
            .chat-input-form {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            #messageInput {
                flex: 1;
                padding: 10px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 20px;
                font-size: 14px;
                outline: none;
                background: #f5f5f5;
            }
            #messageInput:focus {
                border-color: #4285f4;
                background: white;
            }
            #sendButton {
                background: transparent;
                border: none;
                cursor: pointer;
                padding: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            #sendButton:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .send-icon {
                width: 20px;
                height: 20px;
                opacity: 0.6;
            }
            .loading {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #4285f4;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .error {
                color: #e74c3c;
                padding: 10px;
                background: #fee;
                border-radius: 8px;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <span class="chat-title">Chat</span>
                <button class="wave-button" id="waveButton">wave</button>
            </div>
            <div class="chat-messages" id="chatMessages">
                <div class="message assistant">
                    <div class="message-bubble">
                        Welcome to the 10K for 2K program! What's on your mind today? Let's get those questions answered and get you on the fast track to success!
                    </div>
                </div>
            </div>
            <div class="chat-input-container">
                <form class="chat-input-form" id="chatForm">
                    <input type="text" id="messageInput" placeholder="Ask something..." />
                    <button type="submit" id="sendButton">
                        <svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </form>
            </div>
        </div>
        <script>
            let authToken = null;
            let conversationHistory = [];
            const STORAGE_KEY = 'chatbot_conversation_history';
            const TOKEN_STORAGE_KEY = 'chatbot_auth_token';

            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const chatForm = document.getElementById('chatForm');
            const chatMessages = document.getElementById('chatMessages');
            const waveButton = document.getElementById('waveButton');

            // Load token from localStorage or URL parameter
            function getAuthToken() {
                // Check localStorage first
                const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
                if (storedToken) {
                    return storedToken;
                }
                // Check URL parameters (for Kajabi integration)
                const urlParams = new URLSearchParams(window.location.search);
                const tokenParam = urlParams.get('token');
                if (tokenParam) {
                    localStorage.setItem(TOKEN_STORAGE_KEY, tokenParam);
                    return tokenParam;
                }
                return null;
            }

            // Load conversation history from localStorage
            function loadConversationHistory() {
                const stored = localStorage.getItem(STORAGE_KEY);
                if (stored) {
                    try {
                        const history = JSON.parse(stored);
                        conversationHistory = history.messages || [];
                        // Restore messages to UI
                        history.messages?.forEach(msg => {
                            if (msg.role === 'assistant' && msg.content) {
                                addMessageToUI('assistant', msg.content, false);
                            }
                        });
                    } catch (e) {
                        console.error('Error loading conversation history:', e);
                    }
                }
            }

            // Save conversation history to localStorage
            function saveConversationHistory() {
                try {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify({
                        messages: conversationHistory,
                        lastUpdated: new Date().toISOString()
                    }));
                } catch (e) {
                    console.error('Error saving conversation history:', e);
                }
            }

            // Initialize
            authToken = getAuthToken();
            if (authToken) {
                loadConversationHistory();
            } else {
                // If no token, show message
                addMessageToUI('assistant', 'Please provide an access token to start chatting.', false);
            }

            waveButton.addEventListener('click', () => {
                const waveMessage = 'wave';
                messageInput.value = waveMessage;
                chatForm.dispatchEvent(new Event('submit'));
            });

            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const message = messageInput.value.trim();
                if (!message) return;

                if (!authToken) {
                    addMessageToUI('assistant', 'Please provide an access token to start chatting.', false);
                    return;
                }

                addMessageToUI('user', message);
                messageInput.value = '';
                sendButton.disabled = true;
                sendButton.innerHTML = '<div class="loading"></div>';

                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify({
                            message: message,
                            conversation_history: conversationHistory
                        })
                    });

                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get response');
                    }

                    const data = await response.json();
                    addMessageToUI('assistant', data.response);
                    conversationHistory.push({role: 'user', content: message});
                    conversationHistory.push({role: 'assistant', content: data.response});
                    saveConversationHistory();
                } catch (error) {
                    addMessageToUI('assistant', `Error: ${error.message}`, true);
                } finally {
                    sendButton.disabled = false;
                    sendButton.innerHTML = '<svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
                }
            });

            function addMessageToUI(role, content, isError = false) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;
                if (isError) messageDiv.classList.add('error');
                
                const bubble = document.createElement('div');
                bubble.className = 'message-bubble';
                // Preserve line breaks and format text
                bubble.innerHTML = content.replace(/\\n/g, '<br>');
                messageDiv.appendChild(bubble);
                
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return html_content


@app.post("/api/tokens", response_model=TokenResponse)
async def create_token(token_data: TokenCreate):
    """
    Create a new access token for a user.
    This endpoint should be protected and only accessible by admins.
    In production, integrate this with Kajabi's webhook system.
    """
    token = secrets.token_urlsafe(32)
    TOKEN_DB[token] = {
        "user_id": token_data.user_id,
        "created_at": datetime.now().isoformat(),
        "active": True
    }
    # Save tokens to file
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(TOKEN_DB, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save tokens to file: {e}")
    return TokenResponse(token=token)


@app.post("/auth/generate-token")
async def generate_token_auth(
    user_id: str = Query(...),
    secret_key: str = Query(...)
):
    """
    Generate token endpoint for Kajabi integration.
    Matches the endpoint used in Kajabi code.
    """
    # Verify admin secret key
    admin_secret = os.getenv("ADMIN_SECRET_KEY", SECRET_KEY)
    if secret_key != admin_secret:
        raise HTTPException(status_code=401, detail="Invalid secret key")
    
    # Check if user already has an active token
    existing_token = None
    for token, token_data in TOKEN_DB.items():
        if (token_data.get("user_id") == user_id and 
            token_data.get("active", True)):
            existing_token = token
            break
    
    if existing_token:
        return {"token": existing_token}
    
    # Create new token
    token = secrets.token_urlsafe(32)
    TOKEN_DB[token] = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "active": True
    }
    
    # Save tokens to file
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(TOKEN_DB, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save tokens to file: {e}")
    
    return {"token": token}


@app.get("/api/tokens")
async def list_tokens():
    """
    List all tokens (admin only).
    In production, protect this endpoint properly.
    """
    return {
        "tokens": [
            {"token": token[:8] + "...", "user_id": data["user_id"], "active": data["active"]}
            for token, data in TOKEN_DB.items()
        ]
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    """
    Main chat endpoint that uses Gemini FileSearch for RAG.
    Requires valid bearer token authentication.
    """
    if not gemini_client:
        raise HTTPException(status_code=500, detail="Gemini client not initialized")
    
    if not GEMINI_STORE_ID:
        raise HTTPException(status_code=500, detail="GEMINI_STORE_ID not configured")

    try:
        # Build conversation history
        contents = []
        for msg in request.conversation_history:
            contents.append({
                "role": msg.role,
                "parts": [{"text": msg.content}]
            })
        
        # Add current user message
        contents.append({
            "role": "user",
            "parts": [{"text": request.message}]
        })

        # Generate response with FileSearch
        # Note: FileSearch may need to be passed differently depending on SDK version
        # Try using the tools parameter with dict format that matches REST API
        try:
            # Try with dict format for tools (matches REST API structure)
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                tools=[{
                    "file_search": {
                        "file_search_store_names": [GEMINI_STORE_ID]
                    }
                }],
                config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                }
            )
        except (TypeError, AttributeError) as e:
            # Fallback: Try without tools parameter and see if FileSearch is auto-enabled
            # Some SDK versions may handle FileSearch differently
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                }
            )
            # Note: If this doesn't work, we may need to update the SDK or use REST API

        # Extract response text
        response_text = response.text if hasattr(response, 'text') else str(response)
        
        # Extract sources if available
        sources = []
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'grounding_metadata'):
                    if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                        for chunk in candidate.grounding_metadata.grounding_chunks:
                            sources.append({
                                "file_uri": getattr(chunk, 'file_uri', ''),
                                "chunk_index": getattr(chunk, 'chunk_index', None)
                            })

        # Save to conversation history if conversation_id provided
        if request.conversation_id:
            user_id = token_data.get("user_id", "unknown")
            conversations = CHAT_HISTORY_DB.get(user_id, [])
            conversation = next(
                (conv for conv in conversations if conv["id"] == request.conversation_id),
                None
            )
            if conversation:
                conversation["messages"].append({"role": "user", "content": request.message})
                conversation["messages"].append({"role": "assistant", "content": response_text})
                conversation["updated_at"] = datetime.now().isoformat()
                
                # Update title if it's still "New Chat"
                if conversation["title"] == "New Chat":
                    conversation["title"] = request.message[:50] + ("..." if len(request.message) > 50 else "")
                
                save_chat_history()

        return ChatResponse(response=response_text, sources=sources)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "gemini_configured": gemini_client is not None,
        "store_configured": bool(GEMINI_STORE_ID)
    }


@app.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify server is running"""
    return {
        "status": "ok",
        "message": "Server is running",
        "endpoints": {
            "/embed": "Embeddable chatbot UI",
            "/chat": "Full page chatbot UI",
            "/api/health": "Health check",
            "/auth/generate-token": "Generate auth token"
        }
    }


# Chat History Endpoints
@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    token_data: dict = Depends(verify_token)
):
    """Create a new conversation"""
    user_id = token_data.get("user_id", "unknown")
    conversation_id = secrets.token_urlsafe(16)
    now = datetime.now().isoformat()
    
    if user_id not in CHAT_HISTORY_DB:
        CHAT_HISTORY_DB[user_id] = []
    
    title = conversation.title or "New Chat"
    new_conversation = {
        "id": conversation_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": []
    }
    
    CHAT_HISTORY_DB[user_id].insert(0, new_conversation)
    save_chat_history()
    
    return ConversationResponse(
        id=conversation_id,
        title=title,
        created_at=now,
        updated_at=now
    )


@app.get("/api/conversations", response_model=ConversationListResponse)
async def list_conversations(
    search: Optional[str] = None,
    token_data: dict = Depends(verify_token)
):
    """List all conversations for the user, optionally filtered by search"""
    user_id = token_data.get("user_id", "unknown")
    conversations = CHAT_HISTORY_DB.get(user_id, [])
    
    if search:
        search_lower = search.lower()
        conversations = [
            conv for conv in conversations
            if search_lower in conv.get("title", "").lower()
        ]
    
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=conv["id"],
                title=conv["title"],
                created_at=conv["created_at"],
                updated_at=conv["updated_at"]
            )
            for conv in conversations
        ]
    )


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    token_data: dict = Depends(verify_token)
):
    """Get a specific conversation with its messages"""
    user_id = token_data.get("user_id", "unknown")
    conversations = CHAT_HISTORY_DB.get(user_id, [])
    
    conversation = next(
        (conv for conv in conversations if conv["id"] == conversation_id),
        None
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationDetailResponse(
        id=conversation["id"],
        title=conversation["title"],
        created_at=conversation["created_at"],
        updated_at=conversation["updated_at"],
        messages=[
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in conversation.get("messages", [])
        ]
    )


@app.post("/api/conversations/{conversation_id}/messages")
async def add_message_to_conversation(
    conversation_id: str,
    message: ChatMessage,
    token_data: dict = Depends(verify_token)
):
    """Add a message to a conversation"""
    user_id = token_data.get("user_id", "unknown")
    conversations = CHAT_HISTORY_DB.get(user_id, [])
    
    conversation = next(
        (conv for conv in conversations if conv["id"] == conversation_id),
        None
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation["messages"].append({
        "role": message.role,
        "content": message.content
    })
    
    # Update title if it's the first user message
    if message.role == "user" and conversation["title"] == "New Chat":
        # Use first 50 chars of message as title
        conversation["title"] = message.content[:50] + ("..." if len(message.content) > 50 else "")
    
    conversation["updated_at"] = datetime.now().isoformat()
    save_chat_history()
    
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

