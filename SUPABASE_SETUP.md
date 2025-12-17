# 🔗 Supabase Database Setup

## Step 1: Get Your Connection String

1. In your Supabase dashboard, click on **Settings** (gear icon in left sidebar)
2. Go to **Database** section
3. Scroll down to **Connection string**
4. Under **URI**, copy the connection string
5. It will look like:
   ```
   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

## Step 2: Create Database Tables

You have two options:

### Option A: Use SQL Editor (Recommended)

1. Click **SQL Editor** in the left sidebar
2. Click **New query**
3. Paste this SQL:

```sql
-- Create User table
CREATE TABLE IF NOT EXISTS "user" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);

-- Create Habit table
CREATE TABLE IF NOT EXISTS habit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    emoji VARCHAR(10),
    category VARCHAR(50),
    goal INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for user_id
CREATE INDEX IF NOT EXISTS idx_habit_user_id ON habit(user_id);

-- Create HabitLog table
CREATE TABLE IF NOT EXISTS habit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    habit_id UUID NOT NULL REFERENCES habit(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, habit_id, date)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_habit_log_user_id ON habit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_log_habit_id ON habit_log(habit_id);
CREATE INDEX IF NOT EXISTS idx_habit_log_date ON habit_log(date);
```

4. Click **Run** (or press Ctrl+Enter)
5. You should see "Success. No rows returned"

### Option B: Use Table Editor

1. Click **Table Editor** in left sidebar
2. Create each table manually (more time-consuming)

## Step 3: Verify Tables Created

1. Go to **Table Editor** in left sidebar
2. You should see 3 tables:
   - `user`
   - `habit`
   - `habit_log`

## Step 4: Get Connection String for Vercel

1. Go to **Settings** → **Database**
2. Scroll to **Connection string**
3. Under **URI**, copy the connection string
4. **Important**: You'll need the **pooled connection** string for serverless (Vercel)
5. It should look like:
   ```
   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
   ```

## Step 5: Add to Vercel

1. Go to your Vercel project
2. Settings → Environment Variables
3. Add:
   - **Name**: `DATABASE_URL`
   - **Value**: (paste connection string from Step 4)
   - **Environment**: Production, Preview, Development
4. Save

## Step 6: Initialize Database (After Deployment)

After deploying to Vercel, visit:
```
https://your-app.vercel.app/api/migrate
```

This will create the tables if they don't exist (backup method).

## Security Notes

- ✅ Never commit your connection string to GitHub
- ✅ Use environment variables only
- ✅ The connection string includes your password - keep it secret!
- ✅ Supabase automatically handles SSL/TLS encryption

## Troubleshooting

### Connection Issues
- Make sure you're using the **pooled connection** string for Vercel
- Check that your password is correct
- Verify the connection string format

### Table Creation Issues
- Make sure you're in the correct project
- Check SQL syntax
- Verify you have permissions

---

**Your Supabase database is now ready to connect to your app!** 🚀

