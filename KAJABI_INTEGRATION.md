# Kajabi Integration Guide

## New Chatbot UI with Chat History & Search

The new chatbot UI matches the design exactly with:
- ✅ Left sidebar with Chat History
- ✅ Search functionality for conversations
- ✅ Full-screen responsive layout
- ✅ Conversation persistence
- ✅ Modern UI matching the design

## How to Embed in Kajabi

Replace your current Kajabi code with this:

```html
<!-- SLR Lounge Chatbot - New UI with Chat History -->
<div id="chatbot-container" style="width: 100%; height: 700px; margin: 20px 0; border: none;">
  <iframe 
    id="chatbot-iframe"
    src=""
    style="width: 100%; height: 100%; border: none;"
    allow="microphone">
  </iframe>
</div>

<script>
(async function() {
  const container = document.getElementById('chatbot-container');
  const iframe = document.getElementById('chatbot-iframe');
  
  // Initial loading state
  container.innerHTML = '<div style="padding: 40px; text-align: center; color: #666;"><p>Loading chatbot...</p></div>';
  
  try {
    // Kajabi user ID
    const userId = '{{ current_user.id }}';
    
    // ADMIN_SECRET_KEY from Render → chatbot-api → Environment
    const adminSecret = 'VOk9niAXX3QwLfvb1Cdqb-uADEIue_BUbmMuljZwraA';
    
    // Generate token
    const response = await fetch(
      `https://chatbot-api-odi0.onrender.com/auth/generate-token?user_id=${userId}&secret_key=${adminSecret}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }
    );
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    const data = await response.json();
    const token = data.token;
    
    // Load the chatbot UI with token
    const chatbotUrl = `https://chatbot-api-odi0.onrender.com/embed?token=${encodeURIComponent(token)}`;
    
    // Restore iframe
    container.innerHTML = '<iframe id="chatbot-iframe" src="' + chatbotUrl + '" style="width: 100%; height: 100%; border: none;" allow="microphone"></iframe>';
    
  } catch (error) {
    console.error('Error loading chatbot:', error);
    container.innerHTML =
      '<div style="padding: 40px; text-align: center; color: #666;">' +
        '<p style="font-size: 16px; margin-bottom: 10px;">Unable to load chatbot.</p>' +
        '<p style="font-size: 14px; margin-bottom: 20px;">Please refresh the page or contact support.</p>' +
        '<p style="font-size: 12px; color: #999;">Error: ' + error.message + '</p>' +
      '</div>';
  }
})();
</script>
```

## Alternative: Direct Embed (No iframe)

**Note:** This method loads the chatbot HTML directly. Make sure your API server allows CORS from your Kajabi domain.

```html
<!-- SLR Lounge Chatbot - Direct Embed -->
<div id="chatbot-container" style="width: 100%; height: 700px; margin: 20px 0; border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden;">&nbsp;</div>

<script>
(async function() {
  const container = document.getElementById('chatbot-container');
  
  container.innerHTML = '<div style="padding: 40px; text-align: center; color: #666;"><p>Loading chatbot...</p></div>';
  
  try {
    const userId = '{{ current_user.id }}';
    const adminSecret = 'VOk9niAXX3QwLfvb1Cdqb-uADEIue_BUbmMuljZwraA';
    
    // Generate token
    const response = await fetch(
      `https://chatbot-api-odi0.onrender.com/auth/generate-token?user_id=${userId}&secret_key=${adminSecret}`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' } }
    );
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    const data = await response.json();
    const token = data.token;
    
    // Create iframe with token
    const iframe = document.createElement('iframe');
    iframe.src = `https://chatbot-api-odi0.onrender.com/embed?token=${encodeURIComponent(token)}`;
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.allow = 'microphone';
    
    container.innerHTML = '';
    container.appendChild(iframe);
    
  } catch (error) {
    console.error('Error loading chatbot:', error);
    container.innerHTML = 
      '<div style="padding: 40px; text-align: center; color: #666;">' +
        '<p style="font-size: 16px; margin-bottom: 10px;">Unable to load chatbot.</p>' +
        '<p style="font-size: 14px; margin-bottom: 20px;">Please refresh the page or contact support.</p>' +
        '<p style="font-size: 12px; color: #999;">Error: ' + error.message + '</p>' +
      '</div>';
  }
})();
</script>
```

## Features

### Chat History Sidebar
- Displays all past conversations
- Click any conversation to load it
- Shows conversation title and timestamp
- Active conversation is highlighted

### Search Functionality
- Type in the search box to filter conversations
- Searches conversation titles
- Real-time filtering as you type

### New Chat Button
- Click "+ New Chat" to start a fresh conversation
- Previous conversations are preserved

### Conversation Persistence
- All conversations are saved automatically
- Conversations persist across page refreshes
- Each user has their own conversation history

## API Endpoints Used

- `GET /embed` - Main chatbot UI
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations` - List conversations (with optional search)
- `GET /api/conversations/{id}` - Get conversation details
- `POST /api/chat` - Send message (saves to conversation)

## Styling

The UI matches the design with:
- Light brown/beige accent color (#d4a574)
- Clean white background
- Gray message bubbles
- Modern, minimalist design
- Full-screen responsive layout

## Testing the Endpoint

Before embedding in Kajabi, test that the endpoint is accessible:

1. **Test the embed endpoint directly:**
   ```
   https://chatbot-api-odi0.onrender.com/embed?token=YOUR_TEST_TOKEN
   ```
   (Replace `YOUR_TEST_TOKEN` with a token generated via `/auth/generate-token`)

2. **Test the health endpoint:**
   ```
   https://chatbot-api-odi0.onrender.com/api/health
   ```

3. **Test the token generation:**
   ```
   POST https://chatbot-api-odi0.onrender.com/auth/generate-token?user_id=test123&secret_key=YOUR_SECRET_KEY
   ```

## Troubleshooting

### "Not Found" Error

If you get a `{"detail":"Not Found"}` error:

1. **Check the endpoint URL**: Make sure you're using the correct base URL:
   - Production: `https://chatbot-api-odi0.onrender.com`
   - Local: `http://localhost:8000`

2. **Verify the endpoint exists**: Test `/test` endpoint:
   ```
   https://chatbot-api-odi0.onrender.com/test
   ```
   This should return a list of available endpoints.

3. **Check server is running**: Make sure your FastAPI server is running and accessible.

4. **Check CORS**: If loading from Kajabi, ensure CORS is enabled (already configured in the code).

### Other Common Issues

1. **Chatbot not loading**: 
   - Check that the API URL is correct and accessible
   - Check browser console for errors
   - Verify the token is being generated correctly

2. **Token errors**: 
   - Verify the admin secret key matches your Render environment variable `ADMIN_SECRET_KEY`
   - If not set, it defaults to `SECRET_KEY`
   - Check that the token generation endpoint is working

3. **Conversations not saving**: 
   - Check browser console for API errors
   - Verify the user_id is being passed correctly
   - Check server logs for errors

4. **Search not working**: 
   - Ensure you're using the latest code with search functionality
   - Check browser console for JavaScript errors
   - Verify the `/api/conversations` endpoint is accessible

5. **Iframe not loading**:
   - Check browser console for CORS errors
   - Verify the iframe `src` URL is correct
   - Make sure the token is included in the URL query parameter
