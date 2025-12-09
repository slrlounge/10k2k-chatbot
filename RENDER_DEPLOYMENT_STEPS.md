# Render.com Deployment - Step-by-Step Guide

## 🎯 Quick Deployment Checklist

Follow these steps in order:

1. ✅ **Deploy ChromaDB** (Database service)
2. ✅ **Deploy FastAPI API** (Backend service)
3. ✅ **Deploy Frontend** (Netlify/Vercel)
4. ✅ **Configure Environment Variables**
5. ✅ **Test Everything**

---

## Step 1: Deploy ChromaDB on Render

### Configuration Settings:

1. **Source Code:**
   - Connect your Git provider (GitHub/GitLab/Bitbucket)
   - Select your repository

2. **Service Configuration:**
   - **Name:** `chromadb` (or `chatbot-chromadb`)
   - **Language:** Select **"Docker"** (not Node/Python)
   - **Branch:** `main` (or your default branch)
   - **Region:** Choose closest to your users (e.g., "Oregon (US West)")
   - **Root Directory:** (leave empty)
   - **Build Command:** (leave empty - Docker handles this)
   - **Start Command:** (leave empty - Docker handles this)

3. **Docker Settings:**
   - **Dockerfile Path:** `Dockerfile.chroma`
   - **Docker Context:** `.`

4. **Plan:**
   - Select **"Starter"** ($7/month)

5. **Environment Variables:**
   ```
   IS_PERSISTENT=TRUE
   ANONYMIZED_TELEMETRY=FALSE
   ```

6. **Click "Create Web Service"**

7. **Wait for deployment** (2-5 minutes)

8. **Copy the service URL** (e.g., `https://chromadb-xxxx.onrender.com`)
   - Also note the **internal hostname** (usually just `chromadb`)

---

## Step 2: Deploy FastAPI API on Render

### Configuration Settings:

1. **Source Code:**
   - Connect same Git repository
   - Select same branch

2. **Service Configuration:**
   - **Name:** `chatbot-api` (or `10k2k-chatbot-api`)
   - **Language:** Select **"Docker"**
   - **Branch:** `main`
   - **Region:** **Same region as ChromaDB** (important for internal networking)
   - **Root Directory:** (leave empty)
   - **Build Command:** (leave empty)
   - **Start Command:** (leave empty - Docker handles this)

3. **Docker Settings:**
   - **Dockerfile Path:** `Dockerfile`
   - **Docker Context:** `.`

4. **Plan:**
   - Select **"Starter"** ($7/month)

5. **Environment Variables:**
   
   **Required:**
   ```
   ENVIRONMENT=production
   CHROMA_HOST=chromadb
   CHROMA_PORT=8000
   COLLECTION_NAME=10k2k_transcripts
   OPENAI_API_KEY=sk-your-openai-key-here
   ENABLE_AUTH=true
   KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
   LOG_LEVEL=INFO
   ```
   
   **Authentication (Generate these first):**
   ```python
   import secrets
   print("AUTH_SECRET_KEY:", secrets.token_urlsafe(32))
   print("ADMIN_SECRET_KEY:", secrets.token_urlsafe(32))
   ```
   
   Then add:
   ```
   AUTH_SECRET_KEY=paste-generated-key-here
   ADMIN_SECRET_KEY=paste-generated-key-here
   ```
   
   **CORS (Add after frontend is deployed):**
   ```
   ALLOWED_ORIGINS=https://your-frontend.netlify.app,https://www.slrloungeworkshops.com
   ```
   (Update this after you deploy the frontend)

6. **Health Check Path:**
   - Set to: `/health`

7. **Click "Create Web Service"**

8. **Wait for deployment** (3-7 minutes)

9. **Copy the API URL** (e.g., `https://chatbot-api-xxxx.onrender.com`)

10. **Test Health Check:**
    ```bash
    curl https://chatbot-api-xxxx.onrender.com/health
    ```
    Should return: `{"status": "healthy", "environment": "production"}`

---

## Step 3: Deploy Frontend to Netlify

### Option A: Netlify (Recommended)

1. **Go to Netlify Dashboard**
   - Visit: https://app.netlify.com

2. **Add New Site → Import from Git**
   - Connect your Git provider
   - Select your repository

3. **Build Settings:**
   - **Base directory:** (leave empty)
   - **Build command:** (leave empty - we'll use environment variables)
   - **Publish directory:** `web`

4. **Environment Variables:**
   - Go to: Site Settings → Environment Variables
   - Add:
     ```
     API_URL=https://chatbot-api-xxxx.onrender.com
     KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
     ```
   - Replace `chatbot-api-xxxx.onrender.com` with your actual API URL

5. **Deploy**
   - Click "Deploy site"
   - Wait for deployment
   - Copy site URL (e.g., `https://your-chatbot.netlify.app`)

6. **Update API CORS:**
   - Go back to Render → chatbot-api service
   - Update environment variable:
     ```
     ALLOWED_ORIGINS=https://your-chatbot.netlify.app,https://www.slrloungeworkshops.com
     ```
   - Redeploy API service

### Option B: Vercel

1. **Go to Vercel Dashboard**
   - Visit: https://vercel.com

2. **Import Project**
   - Connect Git repository

3. **Configure:**
   - **Framework Preset:** Other
   - **Root Directory:** `web`
   - **Build Command:** (leave empty)
   - **Output Directory:** `.`

4. **Environment Variables:**
   - Add:
     ```
     API_URL=https://chatbot-api-xxxx.onrender.com
     KJ_LOGIN_URL=https://www.slrloungeworkshops.com/login
     ```

5. **Deploy**
   - Click "Deploy"
   - Copy site URL

---

## Step 4: Ingest Data to ChromaDB

### Option 1: Run Ingestion Locally (Pointing to Cloud)

1. **Set environment variables:**
   ```bash
   export CHROMA_HOST=chromadb-xxxx.onrender.com
   export CHROMA_PORT=8000
   export OPENAI_API_KEY=sk-your-key
   ```

2. **Run ingestion:**
   ```bash
   docker-compose -f docker-compose.prod.yml up ingest
   ```

### Option 2: Run Ingestion in Render (One-time Job)

1. **Create Background Worker:**
   - Render Dashboard → New → Background Worker
   - Connect same repository

2. **Configure:**
   - **Name:** `ingest-data`
   - **Dockerfile:** `Dockerfile.ingest`
   - **Environment Variables:** Same as API service

3. **Run:**
   - Deploy and monitor logs
   - Wait for completion

---

## Step 5: Test Everything

### 1. Test API Health
```bash
curl https://chatbot-api-xxxx.onrender.com/health
```

### 2. Test ChromaDB
```bash
curl https://chromadb-xxxx.onrender.com/api/v1/heartbeat
```

### 3. Test Frontend
- Visit your Netlify/Vercel URL
- Open browser console (F12)
- Try asking a question
- Check for errors

### 4. Test Authentication
- Generate test token:
  ```python
  from auth.token_utils import generate_token
  token = generate_token("test_user", expiration_minutes=60)
  print(token)
  ```
- Access: `https://your-frontend.netlify.app/chat.html?token=TOKEN`
- Verify chatbot loads

---

## 🔧 Troubleshooting

### "Service failed to start"
- Check logs in Render dashboard
- Verify environment variables are set correctly
- Check Dockerfile paths are correct

### "Cannot connect to ChromaDB"
- Verify `CHROMA_HOST` is correct internal hostname (`chromadb`)
- Ensure both services are in same region
- Check ChromaDB service is running

### CORS Errors
- Verify `ALLOWED_ORIGINS` includes exact frontend URL
- Include `https://` prefix
- No trailing slashes

### Frontend shows old API URL
- Clear Netlify/Vercel cache
- Rebuild frontend
- Verify environment variables are set

---

## 📋 Quick Reference

### Render Service URLs:
- ChromaDB: `https://chromadb-xxxx.onrender.com`
- API: `https://chatbot-api-xxxx.onrender.com`

### Frontend URL:
- Netlify: `https://your-chatbot.netlify.app`
- Vercel: `https://your-chatbot.vercel.app`

### Environment Variables Checklist:
- [ ] `ENVIRONMENT=production`
- [ ] `CHROMA_HOST=chromadb`
- [ ] `CHROMA_PORT=8000`
- [ ] `OPENAI_API_KEY=sk-...`
- [ ] `AUTH_SECRET_KEY=...`
- [ ] `ADMIN_SECRET_KEY=...`
- [ ] `ALLOWED_ORIGINS=...`
- [ ] `ENABLE_AUTH=true`

---

## ✅ Deployment Complete Checklist

- [ ] ChromaDB deployed and running
- [ ] FastAPI API deployed and running
- [ ] Frontend deployed and running
- [ ] All environment variables set
- [ ] CORS configured correctly
- [ ] Health checks passing
- [ ] Data ingested to ChromaDB
- [ ] Authentication working
- [ ] Frontend can communicate with API
- [ ] Test question answered successfully

---

## 🎉 Next Steps After Deployment

1. **Set up custom domain** (optional)
   - Render: Add custom domain in service settings
   - Netlify: Add custom domain in site settings

2. **Set up monitoring**
   - Render: Enable uptime monitoring
   - Set up alerts for service failures

3. **Integrate with Kajabi**
   - See `KAJABI_EMBED_GUIDE.md`
   - Generate tokens for Kajabi users
   - Embed chatbot in Kajabi lessons

4. **Scale if needed**
   - Monitor usage
   - Upgrade plans if needed
   - Add more workers if traffic increases

