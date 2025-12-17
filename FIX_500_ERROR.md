# 🔧 Fix 500 Error on Vercel

## Step 1: Check Vercel Logs (Most Important!)

1. Go to your Vercel dashboard
2. Click on your project → **"Logs"** tab
3. Look for the error message (usually red text)
4. This will tell us exactly what's wrong

## Common Errors & Fixes

### Error 1: "ModuleNotFoundError" or "ImportError"

**Cause**: Missing dependency or import path issue

**Fix**: 
- Check `requirements-vercel.txt` has all dependencies
- Verify file paths are correct

### Error 2: "OperationalError" or "could not connect to server"

**Cause**: Database connection failed

**Fix**:
1. Go to Vercel → Settings → Environment Variables
2. Verify `DATABASE_URL` is set correctly
3. Use **pooled connection** from Supabase (port 6543)
4. Format: `postgresql://postgres.xxxxx:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
5. Make sure password has no brackets `[YOUR-PASSWORD]` → use actual password

### Error 3: "relation does not exist" or "table does not exist"

**Cause**: Database tables not created

**Fix**:
1. Visit: `https://your-app.vercel.app/api/migrate`
2. Or create tables manually in Supabase SQL Editor

### Error 4: "SECRET_KEY" error

**Cause**: Missing SECRET_KEY environment variable

**Fix**:
1. Go to Vercel → Settings → Environment Variables
2. Add `SECRET_KEY` with a random 32+ character string
3. Generate: `python -c "import secrets; print(secrets.token_hex(32))"`

## Quick Fix Checklist

1. ✅ **Check Vercel Logs** - See actual error
2. ✅ **Set DATABASE_URL** - Use pooled connection string
3. ✅ **Set SECRET_KEY** - Random 32+ character string
4. ✅ **Create Database Tables** - Visit `/api/migrate` or use SQL Editor
5. ✅ **Redeploy** - After fixing env vars, redeploy

## What I Just Fixed

- ✅ Added error handling to prevent crashes
- ✅ Fixed database initialization (won't crash on import)
- ✅ Improved Vercel handler configuration
- ✅ Added better error logging

## Next Steps

1. **Check the Logs tab** in Vercel - this is the most important step!
2. **Share the error message** from logs if you need help
3. **Verify environment variables** are set correctly
4. **Wait for redeployment** (should happen automatically)

---

**The logs will tell us exactly what's wrong!** Check the Logs tab in Vercel. 🔍

