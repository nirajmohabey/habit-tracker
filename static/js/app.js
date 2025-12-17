// Global state
let currentDate = new Date();
let habits = [];
let dailyLogs = {};
let categoryChart = null;
let weeklyChart = null;
let syncInterval = null;
let lastSyncTime = null;
let isSyncing = false;
let pullRefreshStartY = 0;
let pullRefreshActive = false;

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication first
    const authCheck = await checkAuthentication();
    if (!authCheck) {
        window.location.href = '/login';
        return;
    }
    
    setupEventListeners();
    setupPullToRefresh();
    setupRealTimeSync();
    await loadHabits();
    updateMonthDisplay();
    await loadDailyLogs();
    await loadStats();
    displayUserInfo();
    updateSyncStatus('synced');
    
    // Show welcome toast
    showToast('Welcome back!', 'Your habits are synced across all devices', 'success');
});

// Event Listeners
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.dataset.tab;
            switchTab(tab);
        });
    });

    // Month navigation
    document.getElementById('prev-month').addEventListener('click', async () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        updateMonthDisplay();
        await loadDailyLogs();
    });

    document.getElementById('next-month').addEventListener('click', async () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        updateMonthDisplay();
        await loadDailyLogs();
    });

    // Add habit modal
    document.getElementById('add-habit-btn').addEventListener('click', () => {
        document.getElementById('add-habit-modal').style.display = 'block';
    });

    document.querySelector('.close').addEventListener('click', () => {
        document.getElementById('add-habit-modal').style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        const modal = document.getElementById('add-habit-modal');
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Add habit form
    document.getElementById('add-habit-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addHabit();
    });
}

// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');

    if (tabName === 'dashboard') {
        loadStats();
    } else if (tabName === 'settings') {
        loadHabitsList();
    }
    
    // Add haptic feedback on mobile
    if (navigator.vibrate) {
        navigator.vibrate(10);
    }
}

// Load habits
async function loadHabits() {
    try {
        showLoading('tracker-loading');
        const response = await fetch('/api/habits');
        if (await handleApiError(response)) return;
        habits = await response.json();
        renderHabitTable();
        hideLoading('tracker-loading');
    } catch (error) {
        console.error('Error loading habits:', error);
        hideLoading('tracker-loading');
        showToast('Error', 'Failed to load habits', 'error');
    }
}

// Render habit table
function renderHabitTable() {
    const tbody = document.getElementById('habit-tbody');
    const weekHeaders = document.getElementById('week-headers');
    
    // Clear existing content
    tbody.innerHTML = '';
    weekHeaders.innerHTML = '';

    // Get days in current month
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    
    // Generate week headers
    let weekNum = 1;
    let dayCount = 0;
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dayOfWeek = date.getDay();
        
        if (day === 1 || (dayOfWeek === 1 && day > 1)) {
            if (day > 1) weekNum++;
            const weekEnd = Math.min(day + 6, daysInMonth);
            const weekHeader = document.createElement('th');
            weekHeader.className = 'week-header';
            weekHeader.colSpan = Math.min(7, daysInMonth - day + 1);
            weekHeader.innerHTML = `<span class="week-label">WEEK ${weekNum}</span>`;
            weekHeaders.appendChild(weekHeader);
        }
    }

    // Render habits
    habits.forEach(habit => {
        const row = document.createElement('tr');
        
        // Habit name and goal
        const nameCell = document.createElement('td');
        nameCell.className = 'habit-name';
        nameCell.innerHTML = `
            <span class="habit-emoji">${habit.emoji || '✅'}</span>
            <span>${habit.name}</span>
        `;
        
        const goalCell = document.createElement('td');
        goalCell.className = 'habit-goal';
        goalCell.textContent = habit.goal;
        
        row.appendChild(nameCell);
        row.appendChild(goalCell);

        // Day cells
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const dayCell = document.createElement('td');
            dayCell.className = 'day-cell';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'day-checkbox';
            checkbox.dataset.habitId = habit.id;
            checkbox.dataset.date = dateStr;
            
            // Check if this day is completed
            if (dailyLogs[dateStr] && dailyLogs[dateStr][habit.id]) {
                checkbox.checked = true;
            }
            
            checkbox.addEventListener('change', () => {
                toggleHabitLog(habit.id, dateStr, checkbox.checked);
            });
            
            dayCell.appendChild(checkbox);
            row.appendChild(dayCell);
        }
        
        tbody.appendChild(row);
    });
}

// Toggle habit log
async function toggleHabitLog(habitId, date, completed) {
    try {
        const response = await fetch('/api/logs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                habit_id: habitId,
                date: date,
                completed: completed
            })
        });

        if (await handleApiError(response)) return;

        if (response.ok) {
            // Update local state
            if (!dailyLogs[date]) {
                dailyLogs[date] = {};
            }
            dailyLogs[date][habitId] = completed;
            
            // Visual feedback
            const habit = habits.find(h => h.id === habitId);
            if (completed) {
                showToast('Habit Completed!', `${habit?.name || 'Habit'} marked as done`, 'success');
            }
            
            // Update stats if on dashboard
            if (document.getElementById('dashboard-tab').classList.contains('active')) {
                loadStats();
            }
        }
    } catch (error) {
        console.error('Error toggling habit log:', error);
        showToast('Error', 'Failed to update habit', 'error');
    }
}

// Load daily logs
async function loadDailyLogs() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const startDate = `${year}-${String(month + 1).padStart(2, '0')}-01`;
    const endDate = `${year}-${String(month + 1).padStart(2, '0')}-${new Date(year, month + 1, 0).getDate()}`;

    try {
        const response = await fetch(`/api/daily-logs?start_date=${startDate}&end_date=${endDate}`);
        if (await handleApiError(response)) return;
        dailyLogs = await response.json();
        renderHabitTable();
    } catch (error) {
        console.error('Error loading daily logs:', error);
        showToast('Error', 'Failed to load daily logs', 'error');
    }
}

// Update month display
function updateMonthDisplay() {
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    const monthYear = `${monthNames[currentDate.getMonth()]} ${currentDate.getFullYear()}`;
    document.getElementById('current-month-year').textContent = monthYear;
}

// Load stats for dashboard
async function loadStats() {
    try {
        showLoading('dashboard-loading');
        const response = await fetch('/api/stats');
        if (await handleApiError(response)) return;
        const data = await response.json();
        
        renderProgressCards(data.habits);
        renderCategoryChart(data.categories);
        renderWeeklyChart(data.habits);
        hideLoading('dashboard-loading');
    } catch (error) {
        console.error('Error loading stats:', error);
        hideLoading('dashboard-loading');
        showToast('Error', 'Failed to load dashboard', 'error');
    }
}

// Render progress cards
function renderProgressCards(habitsStats) {
    const container = document.getElementById('progress-cards');
    container.innerHTML = '';

    habitsStats.forEach(stat => {
        const card = document.createElement('div');
        card.className = 'progress-card';
        
        const colors = ['#a855f7', '#14b8a6', '#ec4899', '#3b82f6'];
        // Use hash of UUID string for consistent color assignment
        const hash = stat.habit_id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        const color = colors[hash % colors.length];
        
        card.style.borderLeftColor = color;
        
        card.innerHTML = `
            <h3>
                <span>${stat.emoji || '✅'}</span>
                <span>${stat.name}</span>
            </h3>
            <div class="progress-stats">
                <span>${stat.completed} COMPLETED</span>
                <span>${stat.goal} GOAL</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${Math.min(stat.percentage, 100)}%; background: ${color};"></div>
            </div>
            <div class="progress-percentage">${stat.percentage}%</div>
        `;
        
        container.appendChild(card);
    });
}

// Render category chart
function renderCategoryChart(categories) {
    const ctx = document.getElementById('category-chart').getContext('2d');
    
    if (categoryChart) {
        categoryChart.destroy();
    }
    
    categoryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: categories.map(c => c.category),
            datasets: [{
                label: 'Completed',
                data: categories.map(c => c.completed),
                backgroundColor: [
                    'rgba(168, 85, 247, 0.8)',
                    'rgba(20, 184, 166, 0.8)',
                    'rgba(236, 72, 153, 0.8)',
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                ],
                borderColor: [
                    'rgba(168, 85, 247, 1)',
                    'rgba(20, 184, 166, 1)',
                    'rgba(236, 72, 153, 1)',
                    'rgba(59, 130, 246, 1)',
                    'rgba(16, 185, 129, 1)',
                    'rgba(245, 158, 11, 1)',
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#b0b0b0'
                    },
                    grid: {
                        color: '#333333'
                    }
                },
                x: {
                    ticks: {
                        color: '#b0b0b0'
                    },
                    grid: {
                        color: '#333333'
                    }
                }
            }
        }
    });
}

// Render weekly chart
function renderWeeklyChart(habitsStats) {
    const ctx = document.getElementById('weekly-chart').getContext('2d');
    
    // Get current week number
    const today = new Date();
    const startOfYear = new Date(today.getFullYear(), 0, 1);
    const days = Math.floor((today - startOfYear) / (24 * 60 * 60 * 1000));
    const weekNumber = Math.ceil((days + startOfYear.getDay() + 1) / 7);
    
    // Group by category and calculate totals
    const categoryData = {};
    habitsStats.forEach(stat => {
        const cat = stat.category || 'Other';
        if (!categoryData[cat]) {
            categoryData[cat] = { completed: 0, goal: 0 };
        }
        categoryData[cat].completed += stat.completed;
        categoryData[cat].goal += stat.goal;
    });
    
    const labels = Object.keys(categoryData);
    const completed = labels.map(cat => categoryData[cat].completed);
    const goals = labels.map(cat => categoryData[cat].goal);
    
    if (weeklyChart) {
        weeklyChart.destroy();
    }
    
    weeklyChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: completed,
                backgroundColor: [
                    'rgba(168, 85, 247, 0.8)',
                    'rgba(20, 184, 166, 0.8)',
                    'rgba(236, 72, 153, 0.8)',
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                ],
                borderColor: '#0a0a0a',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#b0b0b0',
                        padding: 15
                    }
                }
            }
        }
    });
}

// Add habit
async function addHabit() {
    const name = document.getElementById('habit-name').value;
    const emoji = document.getElementById('habit-emoji').value || '✅';
    const category = document.getElementById('habit-category').value;
    const goal = parseInt(document.getElementById('habit-goal').value);

    try {
        const response = await fetch('/api/habits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                emoji: emoji,
                category: category,
                goal: goal
            })
        });

        if (await handleApiError(response)) return;

        if (response.ok) {
            document.getElementById('add-habit-modal').style.display = 'none';
            document.getElementById('add-habit-form').reset();
            await loadHabits();
            await loadHabitsList();
            showToast('Habit Added', `${name} has been added to your tracker`, 'success');
        }
    } catch (error) {
        console.error('Error adding habit:', error);
        showToast('Error', 'Failed to add habit', 'error');
    }
}

// Load habits list for settings
async function loadHabitsList() {
    try {
        const response = await fetch('/api/habits');
        if (await handleApiError(response)) return;
        const habits = await response.json();
        
        const container = document.getElementById('habits-list');
        container.innerHTML = '';

        habits.forEach(habit => {
            const item = document.createElement('div');
            item.className = 'habit-item';
            item.innerHTML = `
                <div class="habit-item-info">
                    <span style="font-size: 24px;">${habit.emoji || '✅'}</span>
                    <div>
                        <div style="font-weight: 600;">${habit.name}</div>
                        <div style="font-size: 14px; color: var(--text-secondary);">
                            ${habit.category} • Goal: ${habit.goal} days
                        </div>
                    </div>
                </div>
                <div class="habit-item-actions">
                    <button class="btn-danger" onclick="deleteHabit(${habit.id})">Delete</button>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading habits list:', error);
    }
}

// Delete habit
async function deleteHabit(habitId) {
    const habit = habits.find(h => h.id === habitId);
    const habitName = habit ? habit.name : 'Habit';
    
    if (!confirm(`Are you sure you want to delete "${habitName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/habits/${habitId}`, {
            method: 'DELETE'
        });

        if (await handleApiError(response)) return;

        if (response.ok) {
            await loadHabits();
            await loadHabitsList();
            await loadDailyLogs();
            showToast('Habit Deleted', `${habitName} has been removed`, 'success');
        }
    } catch (error) {
        console.error('Error deleting habit:', error);
        showToast('Error', 'Failed to delete habit', 'error');
    }
}

// Make deleteHabit available globally
window.deleteHabit = deleteHabit;

// Toast Notification System
function showToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
}

// Sync Status Management
function updateSyncStatus(status) {
    const syncIcon = document.getElementById('sync-icon');
    const syncText = document.getElementById('sync-text');
    
    if (status === 'syncing') {
        syncIcon.classList.add('syncing');
        syncText.textContent = 'Syncing...';
        isSyncing = true;
    } else if (status === 'synced') {
        syncIcon.classList.remove('syncing');
        syncText.textContent = 'Synced';
        isSyncing = false;
        lastSyncTime = new Date();
    } else if (status === 'error') {
        syncIcon.classList.remove('syncing');
        syncText.textContent = 'Sync failed';
        isSyncing = false;
    }
}

// Real-time Sync System
function setupRealTimeSync() {
    // Sync every 10 seconds
    syncInterval = setInterval(async () => {
        if (!isSyncing) {
            await syncData();
        }
    }, 10000);
    
    // Also sync when tab becomes visible
    document.addEventListener('visibilitychange', async () => {
        if (!document.hidden && !isSyncing) {
            await syncData();
        }
    });
    
    // Sync when window regains focus
    window.addEventListener('focus', async () => {
        if (!isSyncing) {
            await syncData();
        }
    });
}

async function syncData() {
    updateSyncStatus('syncing');
    try {
        // Reload all data
        await Promise.all([
            loadHabits(),
            loadDailyLogs(),
            loadStats()
        ]);
        updateSyncStatus('synced');
    } catch (error) {
        console.error('Sync error:', error);
        updateSyncStatus('error');
        showToast('Sync Failed', 'Could not sync data. Check your connection.', 'error');
    }
}

// Pull to Refresh
function setupPullToRefresh() {
    let touchStartY = 0;
    let touchCurrentY = 0;
    const pullRefresh = document.getElementById('pull-refresh');
    const threshold = 80;
    
    document.addEventListener('touchstart', (e) => {
        if (window.scrollY === 0) {
            touchStartY = e.touches[0].clientY;
            pullRefreshActive = true;
        }
    }, { passive: true });
    
    document.addEventListener('touchmove', (e) => {
        if (!pullRefreshActive) return;
        
        touchCurrentY = e.touches[0].clientY;
        const pullDistance = touchCurrentY - touchStartY;
        
        if (pullDistance > 0 && pullDistance < threshold && window.scrollY === 0) {
            pullRefresh.style.top = `${Math.min(pullDistance, threshold) - 60}px`;
            pullRefresh.classList.add('active');
        }
    }, { passive: true });
    
    document.addEventListener('touchend', async () => {
        if (!pullRefreshActive) return;
        
        const pullDistance = touchCurrentY - touchStartY;
        
        if (pullDistance > threshold && window.scrollY === 0) {
            pullRefresh.classList.add('active');
            await syncData();
            showToast('Refreshed', 'Your data has been updated', 'success');
        }
        
        pullRefresh.style.top = '-60px';
        pullRefresh.classList.remove('active');
        pullRefreshActive = false;
        touchStartY = 0;
        touchCurrentY = 0;
    }, { passive: true });
}

// Loading State Management
function showLoading(elementId) {
    const loading = document.getElementById(elementId);
    if (loading) {
        loading.classList.add('active');
    }
}

function hideLoading(elementId) {
    const loading = document.getElementById(elementId);
    if (loading) {
        loading.classList.remove('active');
    }
}

// Check authentication
async function checkAuthentication() {
    try {
        const response = await fetch('/api/check-auth');
        if (response.status === 401) {
            return false;
        }
        const data = await response.json();
        return data.authenticated;
    } catch (error) {
        console.error('Error checking authentication:', error);
        return false;
    }
}

// Display user info
async function displayUserInfo() {
    try {
        const response = await fetch('/api/check-auth');
        if (response.ok) {
            const data = await response.json();
            if (data.authenticated && data.user) {
                const userInfo = document.getElementById('user-info');
                if (userInfo) {
                    userInfo.textContent = `👤 ${data.user.username}`;
                }
            }
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

// Handle API errors (unauthorized)
async function handleApiError(response) {
    if (response.status === 401) {
        showToast('Session Expired', 'Please log in again', 'warning');
        setTimeout(() => {
            window.location.href = '/login';
        }, 1500);
        return true;
    }
    if (response.status >= 500) {
        showToast('Server Error', 'Please try again later', 'error');
    }
    return false;
}

