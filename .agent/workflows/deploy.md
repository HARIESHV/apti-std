---
description: How to deploy the AptitudePro website safely without losing database data
---

# 🚀 AptitudePro — Safe Deployment Workflow

> ⚠️ **DATABASE SAFETY FIRST**: Every deployment must follow these steps in order.
> NEVER use `db.drop_all()`, `--force`, or reset flags. All migrations are additive-only.

---

## 📋 Pre-Deployment Checklist (Run Locally Before Every Push)

### Step 1: Backup the Database
// turbo
```bash
python backup_db.py
```
This creates a timestamped copy in `/backups/`. Verify it was created before continuing.

### Step 2: Review Your Changes
Check that no code changes include any of these dangerous patterns:
- `db.drop_all()` — NEVER use in production
- `db.session.execute("DROP TABLE ...")` — NEVER
- `SQLALCHEMY_TRACK_MODIFICATIONS = True` with sync — NEVER
- Any `--force-reset` or `--recreate-db` flags

### Step 3: Commit ONLY Code (not database files)
// turbo
```bash
git status
```
Confirm that `.db` files and `instance/` folder appear in `.gitignore` and are NOT staged.

```bash
git add .
git status
```
Make sure `instance/aptipro.db` is NOT in the staged files list.

### Step 4: Write a Safe Commit Message
// turbo
```bash
git commit -m "Update: [describe change] — no schema drops, additive migrations only"
```

### Step 5: Push to GitHub
// turbo
```bash
git push origin main
```

---

## 🌐 Render.com Deployment (Production)

### Environment Variables (Set Once in Render Dashboard)
These must be configured in Render → Your Service → Environment:

| Variable | Value | Notes |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | From Render DB → Internal URL |
| `SECRET_KEY` | Random 64-char string | Generate once, never change |
| `INITIALIZE_DB` | `true` | Safe — migrations are additive only |
| `PYTHON_VERSION` | `3.11.0` | |

### Render Auto-Deploy
After `git push`, Render automatically:
1. Installs `requirements.txt`
2. Starts `gunicorn app:app`
3. `init_db()` runs → creates new tables / adds new columns only
4. **All existing data is preserved** ✅

---

## 🗄️ Database Architecture

### Local Development (SQLite)
- File: `instance/aptipro.db`
- Excluded from Git: ✅ (`.gitignore` covers `*.db` and `instance/`)
- Backup before every push: ✅ (`python backup_db.py`)

### Production (PostgreSQL on Render)
- Managed by Render's PostgreSQL service (`aptipro-db`)
- Persists across all deployments automatically
- Connection via `DATABASE_URL` environment variable
- **Data is never reset by code pushes**

---

## 🛡️ How Safe Migrations Work

Every time the app starts, `init_db()` runs **additive-only** operations:

```
db.create_all()          → Creates NEW tables only. Existing tables untouched.
safe_alter("ALTER TABLE ... ADD COLUMN ...")
                         → Adds NEW columns only. If column exists → silently ignored.
                           NEVER drops rows, tables, or columns.
```

This means you can push code updates **as many times as you want** and the database
will never lose any data.

---

## 🆘 Emergency Recovery

If something goes wrong, restore from backup:
```bash
# Stop the app first, then:
copy backups\aptipro_YYYYMMDD_HHMMSS.db instance\aptipro.db
python app.py
```

For PostgreSQL (production), use Render's built-in database backups from the Render dashboard.

---

## ✅ Safe Deploy Summary

```
1. python backup_db.py     → Backup local DB
2. git add .               → Stage code only (DB excluded by .gitignore)
3. git commit -m "..."     → Commit
4. git push origin main    → Deploy to Render
5. Monitor Render logs     → Confirm "Initialization complete. All existing data preserved."
```
