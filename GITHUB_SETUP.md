# GitHub Setup & Deployment Next Steps

## 🎯 Current Situation

You're looking at your **SLRLounge GitHub organization**. You need to get your chatbot code into a GitHub repository so Render can deploy it.

---

## 📋 Step-by-Step: Get Your Code to GitHub

### Option 1: Create New Repository in SLRLounge Organization

1. **On GitHub (where you are now):**
   - Click the green **"New"** button (top right of repositories section)
   - Or go to: https://github.com/organizations/SLRLounge/repositories/new

2. **Repository Settings:**
   - **Repository name:** `10k2k-chatbot` (or `chatbot-api`)
   - **Description:** "10K/2K AI Mentor Chatbot - RAG-powered assistant"
   - **Visibility:** Private (recommended) or Public
   - **DO NOT** initialize with README, .gitignore, or license (we already have code)
   - Click **"Create repository"**

3. **Copy the repository URL** (e.g., `https://github.com/SLRLounge/10k2k-chatbot.git`)

---

### Option 2: Use Existing Repository

If you already have a repository, use that instead.

---

## 🔧 Push Your Code to GitHub

**Run these commands in your terminal:**

```bash
cd /Users/justinlin/Documents/10K2KChatBot

# Check if git is initialized
git status

# If not initialized, run:
git init
git add .
git commit -m "Initial commit: Production-ready chatbot with Render deployment"

# Add your GitHub repository as remote
git remote add origin https://github.com/SLRLounge/10k2k-chatbot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**If you get authentication errors:**
- Use GitHub CLI: `gh auth login`
- Or use a Personal Access Token: https://github.com/settings/tokens

---

## 🚀 Then Deploy to Render

### Step 1: Go Back to Render

1. **Go to Render Dashboard:** https://dashboard.render.com
2. **Click "New +" → "Web Service"**

### Step 2: Connect GitHub

1. **Source Code:**
   - Click **"Connect account"** under Git Provider
   - Authorize Render to access your GitHub account
   - Select **"SLRLounge"** organization
   - Select your repository: **`10k2k-chatbot`**

### Step 3: Configure ChromaDB Service

**Settings:**
- **Name:** `chromadb`
- **Language:** **Docker** (important!)
- **Branch:** `main`
- **Region:** Choose one (remember it!)
- **Root Directory:** (empty)
- **Build Command:** (empty)
- **Start Command:** (empty)

**Docker:**
- **Dockerfile Path:** `Dockerfile.chroma`
- **Docker Context:** `.`

**Plan:** Starter ($7/month)

**Environment Variables:**
```
IS_PERSISTENT=TRUE
ANONYMIZED_TELEMETRY=FALSE
```

**Click "Create Web Service"** → Wait 2-5 minutes

---

### Step 4: Configure FastAPI API Service

**Create another Web Service:**

**Settings:**
- **Name:** `chatbot-api`
- **Language:** **Docker**
- **Branch:** `main`
- **Region:** **SAME as ChromaDB** (important!)
- **Root Directory:** (empty)
- **Build Command:** (empty)
- **Start Command:** (empty)

**Docker:**
- **Dockerfile Path:** `Dockerfile`
- **Docker Context:** `.`

**Plan:** Starter ($7/month)

**Environment Variables:**
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

**Generate secret keys first:**
```bash
python3 -c "import secrets; print('AUTH_SECRET_KEY:', secrets.token_urlsafe(32))"
python3 -c "import secrets; print('ADMIN_SECRET_KEY:', secrets.token_urlsafe(32))"
```

Then add:
```
AUTH_SECRET_KEY=paste-generated-key-here
ADMIN_SECRET_KEY=paste-generated-key-here
```

**Health Check Path:** `/health`

**Click "Create Web Service"** → Wait 3-7 minutes

---

## ✅ Quick Checklist

- [ ] Code is in GitHub repository
- [ ] Repository is connected to Render
- [ ] ChromaDB service deployed
- [ ] FastAPI API service deployed
- [ ] Environment variables set
- [ ] Health checks passing
- [ ] Frontend deployed (Netlify/Vercel)
- [ ] CORS configured

---

## 🆘 Troubleshooting

### "Repository not found"
- Make sure you authorized Render to access SLRLounge organization
- Check repository name matches exactly

### "Cannot connect to ChromaDB"
- Verify `CHROMA_HOST=chromadb` (not full URL)
- Ensure both services in same region
- Check ChromaDB service is running

### Authentication errors pushing to GitHub
- Use GitHub CLI: `gh auth login`
- Or create Personal Access Token with `repo` scope

---

## 📚 Next Steps After Deployment

1. **Deploy Frontend** → See `RENDER_DEPLOYMENT_STEPS.md`
2. **Ingest Data** → Run ingestion pointing to cloud ChromaDB
3. **Test Everything** → Verify health checks and API calls
4. **Integrate with Kajabi** → See `KAJABI_EMBED_GUIDE.md`

