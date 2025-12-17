# Habit Tracker - Consistency Over Excuses

A production-ready habit tracking web application with secure authentication, real-time sync, and beautiful UI.

> **Status**: Ready for deployment

## Features

- 🔐 **Secure Authentication** - User signup/login with password hashing
- 🔒 **Data Isolation** - Each user's data is completely private
- ✅ **Daily Habit Tracker** - Monthly calendar view with checkboxes
- 📊 **Progress Dashboard** - Charts and completion stats
- 📈 **Category Summary** - Track by category (Fitness, Health, etc.)
- 🎯 **Goal Setting** - Monthly goals for each habit
- 📱 **Cross-Platform** - Works on all devices, installable as PWA
- 🔄 **Real-Time Sync** - Auto-sync across devices
- 🎨 **Modern UI** - Dark theme with smooth animations

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   python app.py
   ```

3. **Access:** `http://localhost:5000`

4. **Create account:** Sign up on the login page

### Deploy to Vercel

1. **Set up database (Supabase - Free):**
   - Go to https://supabase.com
   - Create project → Copy connection string

2. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/habit-tracker.git
   git push -u origin main
   ```

3. **Deploy to Vercel:**
   - Go to https://vercel.com
   - Import GitHub repository
   - Add environment variables:
     - `DATABASE_URL` = (your Supabase connection string)
     - `SECRET_KEY` = (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - Deploy!

4. **Initialize database:**
   - Visit: `https://your-app.vercel.app/api/migrate`

## Project Structure

```
Weekly_Tracker/
├── app.py                 # Main Flask application
├── api/
│   └── index.py          # Vercel serverless entry point
├── templates/            # HTML templates
├── static/               # CSS, JS, assets
├── scripts/
│   └── migrate_db.py     # Database migration script
├── requirements.txt      # Python dependencies
├── requirements-vercel.txt  # Production dependencies
├── vercel.json           # Vercel configuration
└── .gitignore           # Git ignore rules
```

## Database

- **Local Development:** SQLite (`habit_tracker.db`)
- **Production:** PostgreSQL (Supabase/Railway/Neon)
- **Auto-detection:** Uses `DATABASE_URL` environment variable if set

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Production only |
| `SECRET_KEY` | Flask secret key | Yes |
| `FLASK_ENV` | Environment (development/production) | Optional |

## Tech Stack

- **Backend:** Flask (Python)
- **Database:** SQLite (local) / PostgreSQL (production)
- **Frontend:** HTML, CSS, JavaScript
- **Charts:** Chart.js
- **Deployment:** Vercel
- **Database Hosting:** Supabase (recommended)

## Security Features

- Password hashing (PBKDF2)
- Session management
- User data isolation
- SQL injection protection (SQLAlchemy ORM)
- UUID-based IDs

## License

Personal use - modify and customize as needed.

---

**Remember**: This year you're choosing CONSISTENCY over excuses! 💪
