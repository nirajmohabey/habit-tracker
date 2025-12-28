# Test Users Guide

## Overview

This guide provides information about the 25 test users created for thorough website testing.

## Quick Access

**All test users share the same password for easy testing:**
- **Password:** `test123`

## Test User Credentials

| Username | Email | Password |
|----------|-------|----------|
| testuser1 | testuser1@example.com | test123 |
| testuser2 | testuser2@example.com | test123 |
| testuser3 | testuser3@example.com | test123 |
| testuser4 | testuser4@example.com | test123 |
| testuser5 | testuser5@example.com | test123 |
| testuser6 | testuser6@example.com | test123 |
| testuser7 | testuser7@example.com | test123 |
| testuser8 | testuser8@example.com | test123 |
| testuser9 | testuser9@example.com | test123 |
| testuser10 | testuser10@example.com | test123 |
| testuser11 | testuser11@example.com | test123 |
| testuser12 | testuser12@example.com | test123 |
| testuser13 | testuser13@example.com | test123 |
| testuser14 | testuser14@example.com | test123 |
| testuser15 | testuser15@example.com | test123 |
| testuser16 | testuser16@example.com | test123 |
| testuser17 | testuser17@example.com | test123 |
| testuser18 | testuser18@example.com | test123 |
| testuser19 | testuser19@example.com | test123 |
| testuser20 | testuser20@example.com | test123 |
| testuser21 | testuser21@example.com | test123 |
| testuser22 | testuser22@example.com | test123 |
| testuser23 | testuser23@example.com | test123 |
| testuser24 | testuser24@example.com | test123 |
| testuser25 | testuser25@example.com | test123 |

## Data Characteristics

Each test user has been created with realistic variation:

### **Habits**
- **Count:** 3-8 habits per user (randomly selected)
- **Categories:** Health, Fitness, Study, Personal, Productivity
- **Variety:** 24 different habit templates used
- **Examples:**
  - ⏰ Wake up at 7AM
  - 💪 Gym Workout
  - 📚 Study 1 Hour
  - 🧘 Meditation
  - 📝 Write Journal
  - And 19 more...

### **Habit Logs**
- **Duration:** Up to 60 days of tracking data
- **Completion Rates:** 40-90% per habit (varied for realism)
- **Start Dates:** Varied account creation dates (past 60 days)
- **Patterns:** Mix of completed and missed days

### **Account Details**
- **Created Dates:** Spread over the past 60 days
- **Email:** All emails are `testuser{N}@example.com`
- **Password:** All use `test123` for easy testing

## Testing Scenarios

### 1. **User Authentication**
- ✅ Test login with different users
- ✅ Test signup flow (creates new user)
- ✅ Test forgot password (use any test user email)
- ✅ Test password reset flow

### 2. **Habit Management**
- ✅ View habits (3-8 per user)
- ✅ Create new habits
- ✅ Edit existing habits
- ✅ Delete habits
- ✅ Test different categories

### 3. **Daily Tracker**
- ✅ View past 60 days of data
- ✅ Mark/unmark habits for today
- ✅ View missed days (red crosses)
- ✅ Test auto-mark functionality
- ✅ Test inline editing

### 4. **Dashboard**
- ✅ View stats (varies by user)
- ✅ View monthly heatmap (60 days of data)
- ✅ View category breakdown
- ✅ View badges (varies by completion)
- ✅ View AI insights (personalized per user)

### 5. **Settings**
- ✅ Test theme switching
- ✅ Test auto-mark toggle
- ✅ Test notification preferences
- ✅ View account details (varies by creation date)

### 6. **Performance Testing**
- ✅ Test with users having many habits (up to 8)
- ✅ Test with users having many logs (hundreds)
- ✅ Test dashboard loading with varied data
- ✅ Test sync functionality

### 7. **Edge Cases**
- ✅ Users with no habits (testuser19)
- ✅ Users with few logs (testuser16, testuser25)
- ✅ Users with many logs (testuser11: 369 logs)
- ✅ Users with varied completion rates

## Recreating Test Users

If you need to recreate the test users:

```bash
python scripts/create_test_users.py
```

**Note:** The script will skip users that already exist, so you can run it multiple times safely.

## Data Statistics

After running the script, you should have:
- **25 test users** (or fewer if some already existed)
- **~100-200 total habits** (varies)
- **~3000-5000 total habit logs** (varies)

## Tips for Testing

1. **Start with testuser1** - Has moderate data, good for general testing
2. **Use testuser11** - Has the most logs (369), good for performance testing
3. **Use testuser19** - Has no logs, good for testing empty states
4. **Use different users** - Each has different habits and completion patterns
5. **Test edge cases** - Users with very few or very many habits/logs

## Cleanup

To remove all test users (if needed):

```python
from app import app, db, User
with app.app_context():
    test_users = User.query.filter(User.username.like('testuser%')).all()
    for user in test_users:
        db.session.delete(user)
    db.session.commit()
    print(f"Deleted {len(test_users)} test users")
```

---

**Happy Testing! 🚀**

