import { Injectable } from '@angular/core';
import { ApiService } from './api';
import { AuthService } from './auth';

@Injectable({
  providedIn: 'root'
})
export class BrowserNotificationService {
  private notificationCheckInterval: any;
  private lastNotificationDate: string = '';

  constructor(
    private apiService: ApiService,
    private authService: AuthService
  ) {}

  /**
   * Start checking for scheduled browser notifications
   */
  startNotificationScheduler() {
    // Clear any existing interval
    if (this.notificationCheckInterval) {
      clearInterval(this.notificationCheckInterval);
    }

    // Check every minute if it's time to send notification
    this.notificationCheckInterval = setInterval(() => {
      this.checkAndSendNotification();
    }, 60000); // Check every minute

    // Also check immediately
    this.checkAndSendNotification();
  }

  /**
   * Stop the notification scheduler
   */
  stopNotificationScheduler() {
    if (this.notificationCheckInterval) {
      clearInterval(this.notificationCheckInterval);
      this.notificationCheckInterval = null;
    }
  }

  /**
   * Check if it's time to send a notification and send it
   */
  private async checkAndSendNotification() {
    // Check if notifications are enabled in localStorage
    const notificationsEnabled = localStorage.getItem('notificationsEnabled') === 'true';
    if (!notificationsEnabled) {
      return;
    }

    // Check if browser supports notifications
    if (!('Notification' in window)) {
      return;
    }

    // Check if permission is granted
    if (Notification.permission !== 'granted') {
      return;
    }

    try {
      // Get notification preferences from backend
      const preferences = await this.apiService.getNotificationPreferences().toPromise();
      const notificationTime = preferences?.notification_time || '09:00';
      const notificationFrequency = preferences?.notification_frequency || 'daily';

      // Check if it's the right time
      const now = new Date();
      const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
      
      // Only send if it's the exact time (within the same minute)
      if (currentTime !== notificationTime) {
        return;
      }

      // Check if we already sent a notification today
      const today = now.toDateString();
      if (this.lastNotificationDate === today) {
        return;
      }

      // Check frequency - only send daily notifications via browser
      // Weekly summaries are better via email
      // If frequency is 'both', send daily browser notifications
      if (notificationFrequency === 'weekly') {
        return;
      }

      // Get user's habits to personalize the notification
      const habits = await this.apiService.getHabits().toPromise();
      if (!habits || habits.length === 0) {
        return; // No habits to notify about
      }

      const todayLogs = await this.getTodayLogs();

      // Find habits not yet completed today
      const pendingHabits = habits.filter(habit => {
        const log = todayLogs.find(l => l.habit_id === habit.id);
        return !log || !log.completed;
      });

      if (pendingHabits.length === 0) {
        // All habits completed - send congratulatory notification
        this.sendNotification(
          '🎉 Great job!',
          "You've completed all your habits for today! Keep up the amazing work!",
          '/tracker'
        );
      } else {
        // Send reminder with pending habits
        const habitNames = pendingHabits.slice(0, 3).map(h => h.emoji + ' ' + h.name).join(', ');
        const moreText = pendingHabits.length > 3 ? ` and ${pendingHabits.length - 3} more` : '';
        
        this.sendNotification(
          `📋 ${pendingHabits.length} habit${pendingHabits.length > 1 ? 's' : ''} waiting`,
          `Don't forget: ${habitNames}${moreText}`,
          '/tracker'
        );
      }

      // Mark that we sent a notification today
      this.lastNotificationDate = today;
    } catch (error) {
      console.error('Error checking for notifications:', error);
    }
  }

  /**
   * Get today's habit logs
   */
  private async getTodayLogs(): Promise<any[]> {
    try {
      const today = new Date().toISOString().split('T')[0];
      const logs = await this.apiService.getLogs(undefined, today, today).toPromise();
      return logs || [];
    } catch (error) {
      console.error('Error fetching today logs:', error);
      return [];
    }
  }

  /**
   * Send a browser notification
   */
  private sendNotification(title: string, body: string, url?: string) {
    if (Notification.permission !== 'granted') {
      return;
    }

    const notification = new Notification(title, {
      body: body,
      icon: '/assets/icon-192x192.png', // You can add an icon to your assets
      badge: '/assets/icon-192x192.png',
      tag: 'habit-reminder', // Prevents duplicate notifications
      requireInteraction: false,
      silent: false
    });

    // Handle click on notification
    notification.onclick = () => {
      window.focus();
      if (url) {
        window.location.href = url;
      }
      notification.close();
    };

    // Auto-close after 5 seconds
    setTimeout(() => {
      notification.close();
    }, 5000);
  }

  /**
   * Request notification permission
   */
  async requestPermission(): Promise<boolean> {
    if (!('Notification' in window)) {
      return false;
    }

    if (Notification.permission === 'granted') {
      return true;
    }

    if (Notification.permission === 'denied') {
      return false;
    }

    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }
}

