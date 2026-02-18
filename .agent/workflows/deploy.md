---
description: How to deploy the AptitudePro website
---

# Deployment Guide - Worldwide Access 🌍

This guide covers how to deploy the **AptitudePro** website for **worldwide access**.

## 🚀 Quick Deploy to Render.com (Recommended)

### Prerequisites
1. A GitHub account
2. A Render.com account (free tier available)

### Step 1: Push Code to GitHub
// turbo
```bash
git add .
git commit -m "Prepare for worldwide deployment"
git push origin main
```

If you don't have a GitHub repo yet:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/aptitudepro.git
git push -u origin main
```

### Step 2: Deploy on Render
1. Go to [render.com](https://render.com) and sign up/login with GitHub
2. Click **"New +"** → **"Web Service"**
3. Click **"Connect a repository"** and select your repo
4. Configure the service:
   - **Name**: `aptitudepro` (or your choice)
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Instance Type**: `Free`

5. **Add Environment Variables** (Click "Advanced"):
   - `SECRET_KEY` = `your-super-secret-random-key-change-this-123456789`
   - `PYTHON_VERSION` = `3.11.0` (optional, Render auto-detects)

6. Click **"Create Web Service"**

### Step 3: Wait for Deployment
- Render will build and deploy your app (takes 2-5 minutes)
- You'll get a URL like: `https://aptitudepro.onrender.com`
- **Share this URL worldwide!** 🌍

### Step 4: First-Time Setup
1. Visit your Render URL
2. Login with default admin credentials:
   - Username: `admin`
   - Password: `adminpassword`
3. **IMPORTANT**: Change the admin password immediately!

---

## 📊 Database Persistence (Important!)

### Current Setup Issue
- SQLite database (`answer.db`) is **ephemeral** on Render free tier
- Data will be **lost on app restart** or redeployment

### Solution: Upgrade to PostgreSQL
1. In Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Create a free PostgreSQL database
3. Copy the **"Internal Database URL"**
4. In your Web Service, add environment variable:
   - `DATABASE_URL` = `<paste-internal-database-url>`
5. Render will auto-restart your app with persistent database!

---

## 🔐 Security Checklist
- [ ] Change `SECRET_KEY` environment variable to a random string
- [ ] Change default admin password after first login
- [ ] Set up PostgreSQL for data persistence
- [ ] Consider adding rate limiting for production

---

## 🌐 Alternative Deployment Options

### Option 2: Railway.app
1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"** → **"Deploy from GitHub repo"**
3. Select your repository
4. Railway auto-detects Flask and deploys!
5. Add environment variable: `SECRET_KEY`
6. Get your URL: `https://your-app.railway.app`

### Option 3: PythonAnywhere (Free Tier)
1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Sign up for free account
3. Go to **"Web"** tab → **"Add a new web app"**
4. Choose **"Manual configuration"** → **"Python 3.10"**
5. Upload code via Git or Files tab
6. Configure WSGI file to point to your `app.py`
7. Install requirements in virtual environment
8. Reload web app
9. Access at: `https://yourusername.pythonanywhere.com`

---

## 📱 Local Network Access (Already Working)
Your app is already configured for local network access:
```bash
python app.py
```
Access from any device on your network: `http://YOUR_LOCAL_IP:5000`

---

## 🎯 Default Credentials
- **Admin**: `admin` / `adminpassword` (change immediately!)
- **Students**: Register via the registration page

---

## 🐛 Troubleshooting

### Build Fails on Render
- Check that `requirements.txt` is in the root directory
- Verify all dependencies are compatible with Python 3.11

### App Crashes After Deploy
- Check Render logs: Dashboard → Your Service → Logs
- Ensure environment variables are set correctly

### Database Issues
- If using SQLite: Data resets on restart (upgrade to PostgreSQL)
- If using PostgreSQL: Verify `DATABASE_URL` is set correctly

---

## 📞 Support
- Check deployment logs on your hosting platform
- Render logs: Dashboard → Logs tab
- Railway logs: Click on deployment → View logs
