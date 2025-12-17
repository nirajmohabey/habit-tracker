# 🔍 How to Find Your Deployed App

## Step 1: Find Your Vercel URL

1. Go to **https://vercel.com**
2. Sign in with your GitHub account
3. You'll see a list of your projects
4. Click on **"habit-tracker"** (or whatever you named it)
5. At the top, you'll see your deployment URL:
   ```
   https://habit-tracker-xxxxx.vercel.app
   ```
6. **Click on the URL** or copy it

## Step 2: Check Deployment Status

In your Vercel project dashboard:

- ✅ **Green checkmark** = Deployment successful
- ⚠️ **Yellow/orange** = Building or warning
- ❌ **Red X** = Deployment failed

### If Deployment Failed:

1. Click on the failed deployment
2. Check the **"Logs"** tab
3. Look for error messages (usually red text)
4. Common errors:
   - Missing environment variables
   - Database connection error
   - Import errors

## Step 3: Test Your App

Once you have your URL, try:

1. **Main page**: `https://your-app.vercel.app/`
   - Should show login page

2. **Login page**: `https://your-app.vercel.app/login`
   - Should show login form

3. **Database migration**: `https://your-app.vercel.app/api/migrate`
   - Should create tables (visit this first!)

## Step 4: Common Issues

### Issue: "404 Not Found"

**Fix**: 
- Check Vercel logs
- Make sure deployment completed successfully
- Verify `api/index.py` exists

### Issue: "Internal Server Error"

**Fix**:
1. Go to Vercel → Your Project → **Logs** tab
2. Look for the error message
3. Most common: Missing `DATABASE_URL` environment variable

### Issue: Can't See Login Page

**Fix**:
1. Make sure you're visiting the root URL: `https://your-app.vercel.app/`
2. Check browser console for errors (F12)
3. Verify static files are loading

## Step 5: Verify Environment Variables

In Vercel Dashboard → Your Project → **Settings** → **Environment Variables**:

✅ **DATABASE_URL** must be set:
```
postgresql://postgres.xxxxx:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

✅ **SECRET_KEY** must be set:
```
(32+ character random string)
```

## Quick Checklist

- [ ] Found your Vercel project
- [ ] Deployment is successful (green checkmark)
- [ ] Copied your deployment URL
- [ ] Environment variables are set
- [ ] Visited `/api/migrate` to create tables
- [ ] Can see login page at root URL

---

**Your app URL should be visible in your Vercel dashboard!** 🚀

