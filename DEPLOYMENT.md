# Production Deployment Guide

Complete guide for deploying the 10K/2K AI Mentor Chatbot to production cloud infrastructure.

## 📋 Overview

This guide covers deploying:
- **FastAPI Backend** → Render/Railway/DigitalOcean ($7-20/month)
- **ChromaDB Vector Database** → Render/Railway/DigitalOcean ($5-15/month)
- **Frontend Chat UI** → Netlify/Vercel (FREE)
- **Domain & SSL** → Automatic (included)

**Total Cost: ~$12-35/month**

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Kajabi Site   │
│  (Members Only) │
└────────┬────────┘
         │ Token Auth
         ▼
┌─────────────────┐      ┌──────────────┐      ┌─────────────┐
│  Frontend (UI)  │─────▶│ FastAPI API  │─────▶│  ChromaDB   │
│  Netlify/Vercel │      │ Render/etc   │      │ Render/etc  │
│     (FREE)      │      │  ($7-20/mo)  │      │ ($5-15/mo)  │
└─────────────────┘      └──────────────┘      └─────────────┘
         │                        │
         └────────────────────────┘
              OpenAI API Calls
```

---

## 📦 Prerequisites

1. **Accounts:**
   - Render.com account (or Railway/DigitalOcean)
   - Netlify account (or Vercel)
   - OpenAI API key
   - Domain name (optional, $0-12/year)

2. **Code Ready:**
   - All code committed to Git repository
   - Environment variables documented

---

## 🚀 Step 1: Deploy ChromaDB Vector Database

### Option A: Render.com

1. **Create New Web Service:**
   - Go to Render Dashboard → New → Web Service
   - Connect your Git repository
   - Select branch (usually `main`)

2. **Configure Service:**
   - **Name:** `chromadb` (or `chatbot-chromadb`)
   - **Environment:** Docker
   - **Dockerfile Path:** `Dockerfile.chroma`
   - **Docker Context:** `.`
   - **Plan:** Starter ($7/month)

3. **Environment Variables:**
   ```
   IS_PERSISTENT=TRUE
   ANONYMIZED_TELEMETRY=FALSE
   ```

4. **Deploy:**
   - Click "Create Web Service"
   - Wait for deployment (2-5 minutes)
   - Copy the service URL (e.g., `https://chromadb-xxxx.onrender.com`)

5. **Get Internal Host:**
   - Note the internal hostname (for API service)
   - Usually: `chromadb` (if same account) or full URL

### Option B: Railway

1. **Create New Project:**
   - Go to Railway Dashboard → New Project
   - Deploy from GitHub

2. **Add Service:**
   - Click "+ New" → Docker
   - Use `Dockerfile.chroma`
   - Set environment variables

3. **Deploy:**
   - Railway auto-deploys
   - Copy service URL

### Option C: DigitalOcean App Platform

1. **Create App:**
   - Go to DigitalOcean → Apps → Create App
   - Connect GitHub repository

2. **Add Component:**
   - Component Type: Web Service
   - Dockerfile: `Dockerfile.chroma`
   - Plan: Basic ($5/month)

3. **Deploy:**
   - Review and deploy
   - Copy service URL

---

## 🔧 Step 2: Deploy FastAPI Backend

### Option A: Render.com

1. **Create New Web Service:**
   - Go to Render Dashboard → New → Web Service
   - Connect same Git repository

2. **Configure Service:**
   - **Name:** `chatbot-api`
   - **Environment:** Docker
   - **Dockerfile Path:** `Dockerfile`
   - **Docker Context:** `.`
   - **Plan:** Starter ($7/month)

3. **Environment Variables:**
   ```bash
   ENVIRONMENT=production
   CHROMA_HOST=chromadb  # Internal hostname from Step 1
   CHROMA_PORT=8000
   COLLECTION_NAME=10k2k_transcripts
   OPENAI_API_KEY=sk-...  # Your OpenAI API key
   AUTH_SECRET_KEY=...    # Generate secure random string
   ADMIN_SECRET_KEY=...   # Generate secure random string
   KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
   ENABLE_AUTH=true
   ALLOWED_ORIGINS=https://your-frontend.netlify.app,https://www.slrloungeworkshops.com
   LOG_LEVEL=INFO
   ```

4. **Generate Secret Keys:**
   ```python
   import secrets
   print("AUTH_SECRET_KEY:", secrets.token_urlsafe(32))
   print("ADMIN_SECRET_KEY:", secrets.token_urlsafe(32))
   ```

5. **Deploy:**
   - Click "Create Web Service"
   - Wait for deployment
   - Copy the API URL (e.g., `https://chatbot-api-xxxx.onrender.com`)

6. **Test Health Check:**
   ```bash
   curl https://chatbot-api-xxxx.onrender.com/health
   # Should return: {"status": "healthy", "environment": "production"}
   ```

### Option B: Railway

1. **Add Service to Project:**
   - In your Railway project → "+ New" → Docker
   - Use `Dockerfile`

2. **Set Environment Variables:**
   - Same as Render.com above
   - Use Railway's internal service discovery for `CHROMA_HOST`

3. **Deploy:**
   - Railway auto-deploys on git push
   - Copy service URL

### Option C: DigitalOcean App Platform

1. **Add Component:**
   - In your DigitalOcean app → Add Component → Web Service
   - Dockerfile: `Dockerfile`
   - Plan: Basic ($12/month)

2. **Set Environment Variables:**
   - Same as Render.com above

3. **Deploy:**
   - Review and deploy
   - Copy service URL

---

## 🎨 Step 3: Deploy Frontend to Netlify

### Option A: Netlify

1. **Create New Site:**
   - Go to Netlify Dashboard → Add New Site → Import from Git
   - Connect your repository

2. **Build Settings:**
   - **Base directory:** (leave empty)
   - **Build command:** `./build-frontend.sh` (or leave empty if using env vars)
   - **Publish directory:** `web` (or `dist` if using build script)

3. **Environment Variables:**
   - Go to Site Settings → Environment Variables
   - Add:
     ```
     API_URL=https://chatbot-api-xxxx.onrender.com
     KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
     ```

4. **Build Hook (Optional):**
   - If using build script, set:
     ```bash
     API_URL=https://chatbot-api-xxxx.onrender.com
     KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
     ```

5. **Deploy:**
   - Click "Deploy site"
   - Wait for deployment
   - Copy site URL (e.g., `https://your-chatbot.netlify.app`)

6. **Update CORS:**
   - Go back to Render/Railway API service
   - Update `ALLOWED_ORIGINS` to include Netlify URL:
     ```
     ALLOWED_ORIGINS=https://your-chatbot.netlify.app,https://www.slrloungeworkshops.com
     ```
   - Redeploy API service

### Option B: Vercel

1. **Import Project:**
   - Go to Vercel Dashboard → Add New Project
   - Import from Git

2. **Configure:**
   - **Framework Preset:** Other
   - **Root Directory:** `web`
   - **Build Command:** (leave empty)
   - **Output Directory:** `.`

3. **Environment Variables:**
   - Add:
     ```
     API_URL=https://chatbot-api-xxxx.onrender.com
     KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
     ```

4. **Deploy:**
   - Click "Deploy"
   - Copy site URL

---

## 🔗 Step 4: Connect Frontend to Backend

### Update Frontend API URL

**If using Netlify:**
- The frontend already reads `window.API_URL` or uses environment variables
- Netlify will inject these at build time

**If using static build:**
```bash
export API_URL=https://chatbot-api-xxxx.onrender.com
export KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
./build-frontend.sh
# Upload dist/ directory to your hosting
```

### Test Connection

1. Open frontend URL in browser
2. Open browser console (F12)
3. Try asking a question
4. Check Network tab for API calls
5. Verify CORS headers are correct

---

## 🔐 Step 5: Set Up Authentication

### Generate Tokens for Kajabi Users

**Option 1: Use Token Generation Endpoint**

From Kajabi custom code block:
```javascript
fetch('https://chatbot-api-xxxx.onrender.com/auth/generate-token?user_id={{kajabi_user_id}}&secret_key=YOUR_ADMIN_SECRET', {
    method: 'POST'
})
.then(response => response.json())
.then(data => {
    const iframe = document.createElement('iframe');
    iframe.src = `https://your-chatbot.netlify.app/chat.html?token=${data.token}`;
    // ... embed iframe
});
```

**Option 2: Pre-generate Tokens**

```python
from auth.token_utils import generate_token

token = generate_token("kajabi_user_123", expiration_minutes=1440)
print(f"Token: {token}")
```

### Embed in Kajabi

See `KAJABI_EMBED_GUIDE.md` for detailed instructions.

---

## 📊 Step 6: Ingest Data to Cloud ChromaDB

### Option 1: Run Ingestion Locally (Pointing to Cloud)

1. **Set Environment Variables:**
   ```bash
   CHROMA_HOST=chromadb-xxxx.onrender.com  # Your cloud ChromaDB URL
   CHROMA_PORT=8000
   OPENAI_API_KEY=sk-...
   ```

2. **Run Ingestion:**
   ```bash
   docker-compose -f docker-compose.prod.yml up ingest
   ```

### Option 2: Run Ingestion in Cloud

1. **Create One-Time Job:**
   - Render: Create Background Worker
   - Railway: Create one-time deployment
   - Use `Dockerfile.ingest`

2. **Set Environment Variables:**
   - Same as API service
   - Point to cloud ChromaDB

3. **Run:**
   - Deploy and let it run
   - Monitor logs for completion

---

## ✅ Step 7: Verify Deployment

### Health Checks

1. **API Health:**
   ```bash
   curl https://chatbot-api-xxxx.onrender.com/health
   ```

2. **ChromaDB Health:**
   ```bash
   curl https://chromadb-xxxx.onrender.com/api/v1/heartbeat
   ```

3. **Frontend:**
   - Visit frontend URL
   - Check browser console for errors

### Test Authentication

1. Generate test token
2. Access: `https://your-frontend.netlify.app/chat.html?token=TEST_TOKEN`
3. Verify chatbot loads
4. Test asking a question

---

## 🔧 Troubleshooting

### CORS Errors

**Problem:** Frontend can't call API

**Solution:**
1. Check `ALLOWED_ORIGINS` in API environment variables
2. Include exact frontend URL (with https://)
3. Redeploy API service

### ChromaDB Connection Failed

**Problem:** API can't connect to ChromaDB

**Solution:**
1. Verify `CHROMA_HOST` is correct internal hostname
2. Check ChromaDB service is running
3. Verify port is 8000
4. Check service logs

### Authentication Not Working

**Problem:** Tokens rejected

**Solution:**
1. Verify `AUTH_SECRET_KEY` matches between token generation and validation
2. Check token hasn't expired
3. Verify `ENABLE_AUTH=true` in API environment

### Frontend Shows Old API URL

**Problem:** Frontend still using localhost/ngrok

**Solution:**
1. Clear Netlify/Vercel cache
2. Rebuild frontend with correct `API_URL`
3. Check environment variables are set

---

## 📈 Monitoring & Maintenance

### Logs

- **Render:** Dashboard → Service → Logs
- **Railway:** Dashboard → Service → Logs
- **Netlify:** Site Settings → Build & Deploy → Deploy Logs

### Scaling

- **Render:** Upgrade plan for more resources
- **Railway:** Auto-scales based on usage
- **DigitalOcean:** Upgrade component plan

### Updates

1. Push changes to Git
2. Services auto-deploy (if enabled)
3. Monitor deployment logs
4. Test after deployment

---

## 💰 Cost Breakdown

| Service | Provider | Plan | Cost |
|---------|----------|------|------|
| ChromaDB | Render | Starter | $7/mo |
| FastAPI API | Render | Starter | $7/mo |
| Frontend | Netlify | Free | $0/mo |
| Domain | Namecheap | .com | ~$12/year |
| **Total** | | | **~$14/month** |

**Alternative Providers:**
- Railway: Similar pricing (~$5-10/service)
- DigitalOcean: $5-12/service
- Vercel: Free for frontend

---

## 🔄 CI/CD Setup (Optional)

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Trigger Render Deploy
        run: |
          curl -X POST "https://api.render.com/deploy/srv/xxx?key=${{ secrets.RENDER_API_KEY }}"
```

---

## 📚 Additional Resources

- **Render Docs:** https://render.com/docs
- **Railway Docs:** https://docs.railway.app
- **Netlify Docs:** https://docs.netlify.com
- **ChromaDB Docs:** https://docs.trychroma.com

---

## 🆘 Support

If you encounter issues:

1. Check service logs
2. Verify environment variables
3. Test health endpoints
4. Review this guide's troubleshooting section

For code issues, check:
- `DEPLOYMENT.md` (this file)
- `KAJABI_EMBED_GUIDE.md`
- `AUTHENTICATION_SETUP.md`

