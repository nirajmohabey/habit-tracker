# Troubleshooting Guide - Black Screen Issue

## Problem: Blank/Black Screen on `localhost:4200/tracker`

### Quick Checks

1. **Is the backend running?**
   ```bash
   # Check if Flask is running on port 5000
   # You should see: "Running on http://0.0.0.0:5000"
   ```

2. **Is the frontend running?**
   ```bash
   # Check if Angular dev server is running
   # You should see: "Application bundle generation complete"
   ```

3. **Open Browser Console (F12)**
   - Look for red error messages
   - Common errors:
     - `Failed to fetch` - Backend not running
     - `CORS error` - Backend CORS not configured
     - `401 Unauthorized` - Not logged in (expected if not authenticated)

### Step-by-Step Fix

#### Step 1: Verify Backend is Running

**Terminal 1:**
```bash
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
```

If you see errors, fix them first.

#### Step 2: Verify Frontend is Running

**Terminal 2:**
```bash
cd frontend
npm start
```

You should see:
```
✔ Browser application bundle generation complete.
```

#### Step 3: Check Browser Console

1. Open `http://localhost:4200` in your browser
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Look for errors

**Common Issues:**

**Error: "Failed to fetch" or "NetworkError"**
- **Solution:** Backend is not running. Start it with `python app.py`

**Error: "CORS policy"**
- **Solution:** Check `app.py` CORS configuration includes `http://localhost:4200`

**Error: "401 Unauthorized"**
- **This is normal** if you're not logged in. The app should redirect to `/login`

#### Step 4: Check Network Tab

1. Open Developer Tools (F12)
2. Go to **Network** tab
3. Refresh the page
4. Look for failed requests (red)

**Check these requests:**
- `http://localhost:5000/api/check-auth` - Should return 200
- If it fails, backend is not running or CORS is blocking

#### Step 5: Try Direct Login Page

Navigate directly to:
```
http://localhost:4200/login
```

If login page shows, the app is working but you need to log in first.

### Expected Behavior

1. **Not logged in:**
   - Should redirect to `/login`
   - Login page should be visible

2. **Logged in:**
   - Should show the tracker/dashboard
   - Header with username visible

3. **Backend down:**
   - May show black screen
   - Console shows "Failed to fetch" errors
   - **Fix:** Start backend server

### Still Not Working?

1. **Clear browser cache:**
   - Press `Ctrl+Shift+Delete`
   - Clear cache and cookies
   - Refresh page

2. **Check environment configuration:**
   - File: `frontend/src/environments/environment.ts`
   - Should have: `apiUrl: 'http://localhost:5000/api'`

3. **Restart both servers:**
   - Stop both terminals (Ctrl+C)
   - Start backend: `python app.py`
   - Start frontend: `cd frontend && npm start`

4. **Check database:**
   - Make sure database is initialized
   - Visit: `http://localhost:5000/api/migrate`

### Debug Mode

Add this to browser console to see auth state:
```javascript
// In browser console
localStorage.clear();
sessionStorage.clear();
location.reload();
```

### Contact

If none of these work, check:
- Browser console for specific error messages
- Network tab for failed requests
- Backend terminal for error logs
- Frontend terminal for compilation errors

