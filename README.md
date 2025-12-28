# Weekly Tracker - Habit Tracking Application

A full-stack habit tracking application built with Angular 21 frontend and Flask backend.

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 18+** and **npm** (for frontend)
- **SQLite** (included with Python) or **PostgreSQL** (for production)

### Installation

1. **Clone the repository** (if not already done)
   ```bash
   cd Weekly_Tracker
   ```

2. **Install Backend Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Initialize Database** (First time only)
   ```bash
   python app.py
   # Then visit http://localhost:5000/api/migrate in your browser
   # Or use curl: curl http://localhost:5000/api/migrate
   ```

5. **Seed Database with Test Data** (Choose one):

   **Option A: Single Demo User** (Quick testing)
   ```bash
   python scripts/seed_database.py
   ```
   Creates a demo user with sample habits and 30 days of sample data:
   - **Username:** `demo`
   - **Password:** `demo123`
   - **Email:** `demo@example.com`
   
   **Option B: 25 Test Users** (Thorough testing)
   ```bash
   python scripts/create_test_users.py
   ```
   
   **To delete and recreate test users:**
   ```bash
   python scripts/delete_test_users.py
   python scripts/create_test_users.py
   ```
   Creates 25 test users with varied data:
   - **Usernames:** `testuser1` to `testuser25`
   - **Password:** `test123` (same for all)
   - **Emails:** `testuser1@example.com` to `testuser25@example.com`
   
   Each test user includes:
   - 3-8 different habits (randomly selected)
   - 40-90% completion rates (varied per habit)
   - 60 days of habit tracking data
   - Varied account creation dates (past 60 days)
   - Perfect for testing scalability, performance, and features!

## 🏃 Running the Application

You need to run **both** the backend and frontend servers simultaneously.

### Option 1: Two Terminal Windows (Recommended)

**Terminal 1 - Backend (Flask):**
```bash
python app.py
```
Backend will run on: `http://localhost:5000`

**Terminal 2 - Frontend (Angular):**
```bash
cd frontend
npm start
```
Frontend will run on: `http://localhost:4200`

### Option 2: PowerShell (Windows)

**Terminal 1:**
```powershell
python app.py
```

**Terminal 2:**
```powershell
cd frontend
npm start
```

### Option 3: Using npm scripts (if configured)

You can create a script to run both, but for now, use two terminals.

## 🧪 Testing with Demo User

After seeding the database, you can immediately test the application:

1. **Start both servers** (backend and frontend)
2. **Navigate to** `http://localhost:4200`
3. **Login with demo credentials:**
   - Username: `demo`
   - Password: `demo123`
4. **Explore the features:**
   - View 30 days of sample habit data
   - See completed and missed days
   - Test dashboard, settings, and all features
   - Add new habits or modify existing ones

> **Note:** The demo user has sample data from the past 30 days, so you can see how the app works with real data patterns.

## 🌐 Access the Application

Once both servers are running:
- **Frontend**: Open your browser and go to `http://localhost:4200`
- **Backend API**: Available at `http://localhost:5000/api`

## 📝 First Time Setup

1. **Start both servers** (see above)

2. **Create database tables** (if not done during installation):
   - Visit: `http://localhost:5000/api/migrate`
   - Or use curl: `curl http://localhost:5000/api/migrate`

3. **Sign up for an account**:
   - Go to `http://localhost:4200`
   - Click "Sign Up"
   - Create your account
   - Default habits will be created automatically

4. **Start tracking your habits!**

## 🔧 Configuration

### Backend Configuration

Environment variables (optional):
- `SECRET_KEY`: Flask session secret key (auto-generated if not set)
- `DATABASE_URL`: PostgreSQL connection string (uses SQLite if not set)
- `SESSION_COOKIE_SECURE`: Set to `true` for HTTPS (default: `false` for localhost)
- `CORS_ORIGINS`: Comma-separated list of allowed origins (default: localhost URLs)

**Email Configuration (for sending emails to users):**
> **Important:** These are YOUR application's email service credentials, NOT user credentials!
> Your app uses ONE email service account to send emails TO all users.
> Users only provide their email address (where to send), not their email password.
> This is standard practice - like how GitHub, Facebook, etc. send emails from their service.

- `MAIL_SERVER`: SMTP server (default: smtp.gmail.com)
- `MAIL_PORT`: SMTP port (default: 587)
- `MAIL_USE_TLS`: Use TLS (default: true)
- `MAIL_USERNAME`: **YOUR** email service account username (e.g., your-email@gmail.com)
- `MAIL_PASSWORD`: **YOUR** email service password or app password
- `MAIL_DEFAULT_SENDER`: Default sender email (default: noreply@habittracker.com)
- `FRONTEND_URL`: Frontend URL for password reset links (default: http://localhost:4200)

**Example:** If you use Gmail, you would set:
- `MAIL_USERNAME=yourapp@gmail.com` (your Gmail account)
- `MAIL_PASSWORD=xxxx xxxx xxxx xxxx` (Gmail App Password)
- All emails sent by your app will come FROM this account TO your users

### Frontend Configuration

Edit `frontend/src/environments/environment.ts`:
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:5000/api'  // Change if backend runs on different port
};
```

## 🛠️ Development

### Backend Development
- Backend runs with debug mode enabled by default
- Auto-reloads on file changes
- Logs are printed to console

### Frontend Development
- Angular dev server with hot-reload
- Open `http://localhost:4200` in browser
- Changes automatically reload

### Building for Production

**Frontend:**
```bash
cd frontend
npm run build
```
Output will be in `frontend/dist/`

**Backend:**
- Set environment variables for production
- Use a production WSGI server (e.g., Gunicorn)
- Configure PostgreSQL database

## 📁 Project Structure

```
Weekly_Tracker/
├── app.py                 # Flask backend application
├── requirements.txt       # Python dependencies
├── instance/              # SQLite database (created automatically)
│   └── habit_tracker.db
├── frontend/              # Angular frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/    # Angular components
│   │   │   ├── services/      # API and auth services
│   │   │   └── app.routes.ts   # Routing configuration
│   │   └── environments/      # Environment configuration
│   └── package.json
└── README.md
```

## 🐛 Troubleshooting

### Backend Issues

**Port 5000 already in use:**
- Change port in `app.py`: `app.run(debug=True, host='0.0.0.0', port=5001)`
- Update frontend `environment.ts` to match

**Database errors:**
- Delete `instance/habit_tracker.db` and run `/api/migrate` again
- Check database permissions

**CORS errors:**
- Ensure `CORS_ORIGINS` includes your frontend URL
- Check that `supports_credentials=True` is set

### Frontend Issues

**Port 4200 already in use:**
- Angular CLI will prompt to use a different port
- Or specify: `ng serve --port 4201`

**API connection errors:**
- Verify backend is running on port 5000
- Check `environment.ts` has correct API URL
- Check browser console for CORS errors

**Module not found errors:**
- Run `npm install` again in `frontend/` directory
- Delete `node_modules` and `package-lock.json`, then reinstall

## 📚 API Endpoints

- `GET /api/health` - Health check
- `GET /api/check-auth` - Check authentication status
- `POST /login` - User login
- `POST /signup` - User registration
- `GET /logout` - User logout
- `GET /api/habits` - Get all habits
- `POST /api/habits` - Create habit
- `PUT /api/habits/<id>` - Update habit
- `DELETE /api/habits/<id>` - Delete habit
- `GET /api/logs` - Get habit logs
- `POST /api/logs` - Toggle habit log
- `GET /api/stats` - Get statistics
- `GET /api/daily-logs` - Get daily logs
- `POST /api/auto-mark-missed` - Auto-mark missed days
- `GET /api/badges` - Get badges
- `GET /api/insights` - Get AI insights

## 🚢 Deployment

### Vercel (Backend)
- Configure environment variables in Vercel dashboard
- Set `DATABASE_URL` for PostgreSQL
- Set `SECRET_KEY` for sessions
- Deploy using Vercel CLI or GitHub integration

### Frontend Deployment
- Build: `npm run build` in `frontend/` directory
- Deploy `dist/` folder to your hosting service
- Update `environment.prod.ts` with production API URL

## 📄 License

This project is open source and available for personal use.

## 🤝 Support

For issues or questions, check the code comments or create an issue in the repository.
