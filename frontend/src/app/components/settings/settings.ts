import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';
import { ToastService } from '../../services/toast.service';
import { AutoMarkService } from '../../services/auto-mark.service';
import { BrowserNotificationService } from '../../services/browser-notification.service';
import { filter, take } from 'rxjs/operators';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.html',
  styleUrl: './settings.css',
})
export class Settings implements OnInit {
  autoMarkMissed = true;
  notificationsEnabled = false;
  theme = 'dark';
  
  // Email notification preferences
  emailNotificationsEnabled = true;
  notificationTime = '09:00';
  notificationFrequency: 'daily' | 'weekly' | 'both' = 'daily';
  
  accountInfo: {
    username?: string;
    email?: string;
    created_at?: string;
  } = {};

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private toastService: ToastService,
    private router: Router,
    private autoMarkService: AutoMarkService,
    private browserNotificationService: BrowserNotificationService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadSettings();
    // Load account info immediately - first from authService, then from API
    this.loadAccountInfo();
    // Load notification preferences from backend
    this.loadNotificationPreferences();
    
    // Also subscribe to authService to update when user logs in
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        // Update immediately with available data
        if (!this.accountInfo.username || this.accountInfo.username === 'N/A') {
          this.accountInfo = {
            username: user.username || 'N/A',
            email: user.email || 'N/A'
          };
        }
        // Always fetch full info including created_at when user is available
        this.loadAccountInfo();
        // Reload notification preferences when user changes
        this.loadNotificationPreferences();
      }
    });
  }

  loadSettings() {
    // Load preferences from localStorage
    const savedAutoMark = localStorage.getItem('autoMarkMissed');
    if (savedAutoMark !== null) {
      this.autoMarkMissed = savedAutoMark === 'true';
    } else {
      // Default to true if not set
      this.autoMarkMissed = true;
      localStorage.setItem('autoMarkMissed', 'true');
    }

    const savedNotifications = localStorage.getItem('notificationsEnabled');
    if (savedNotifications !== null) {
      this.notificationsEnabled = savedNotifications === 'true';
    }

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light' || savedTheme === 'dark') {
      this.theme = savedTheme;
      // Apply theme on load
      this.applyTheme(savedTheme);
    } else {
      // Default to dark if not set or invalid
      this.theme = 'dark';
      localStorage.setItem('theme', 'dark');
      this.applyTheme('dark');
    }
  }

  async loadAccountInfo() {
    // First try to get from authService immediately (already loaded)
    const currentUser = this.authService.getCurrentUser();
    if (currentUser) {
      // Use current user data immediately
      this.accountInfo = {
        username: currentUser.username || 'N/A',
        email: currentUser.email || 'N/A'
      };
    }
    
    // Then fetch full account info from API (includes created_at)
    try {
      const response = await this.apiService.checkAuth().toPromise();
      
      if (response && response.authenticated && response.user) {
        const created_at = response.user.created_at || response.created_at || response.signup_date || null;
        
        this.accountInfo = {
          username: response.user.username || currentUser?.username || 'N/A',
          email: response.user.email || currentUser?.email || 'N/A',
          created_at: created_at
        };
        
        // Force change detection to update the view
        this.cdr.detectChanges();
      } else if (currentUser) {
        // Keep the data we already have from authService
        // Just update created_at if available
        if (response) {
          const created_at = response.user?.created_at || response.created_at || response.signup_date;
          if (created_at) {
            this.accountInfo.created_at = created_at;
          }
        }
      } else {
        // No user data at all, try to get from authService observable
        this.loadFromAuthService();
      }
    } catch (error: any) {
      console.error('Error loading account info:', error);
      
      // If we don't have account info yet, try authService
      if (!this.accountInfo.username || this.accountInfo.username === 'N/A') {
        this.loadFromAuthService();
      }
      
      if (error.status === 401) {
        this.toastService.warning('Session Expired', 'Please log in again');
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 1500);
      } else if (error.status >= 500) {
        this.toastService.error('Server Error', 'Please try again later');
      }
    }
  }
  
  private loadFromAuthService() {
    this.authService.currentUser$.pipe(
      filter(user => user !== null),
      take(1)
    ).subscribe(user => {
      if (user) {
        this.accountInfo = {
          username: user.username || 'N/A',
          email: user.email || 'N/A'
        };
      }
    });
  }

  onAutoMarkChange() {
    // Save the actual boolean value as string
    const value = this.autoMarkMissed ? 'true' : 'false';
    localStorage.setItem('autoMarkMissed', value);
    
    // Haptic feedback on mobile
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
    
    // Show feedback
    this.toastService.success(
      'Preference Saved', 
      `Auto-mark missed days is now ${this.autoMarkMissed ? 'enabled' : 'disabled'}`
    );
    
    // If enabled, trigger auto-mark immediately for current month if it's in the past
    if (this.autoMarkMissed) {
      // Trigger auto-mark service
      this.autoMarkService.triggerAutoMark();
      
      // Also navigate to tracker to see the results
      const currentUrl = this.router.url;
      if (!currentUrl.includes('/tracker')) {
        setTimeout(() => {
          this.router.navigate(['/tracker']);
        }, 300);
      }
    }
  }

  async loadNotificationPreferences() {
    try {
      const response = await this.apiService.getNotificationPreferences().toPromise();
      if (response) {
        this.emailNotificationsEnabled = response.email_notifications_enabled ?? true;
        this.notificationTime = response.notification_time || '09:00';
        this.notificationFrequency = response.notification_frequency || 'daily';
      }
    } catch (error: any) {
      console.error('Error loading notification preferences:', error);
      // Use defaults if API fails
    }
  }

  async onNotificationsChange() {
    localStorage.setItem('notificationsEnabled', String(this.notificationsEnabled));
    // Haptic feedback on mobile
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
    // Show feedback
    this.toastService.success(
      'Preference Saved', 
      `Notifications are now ${this.notificationsEnabled ? 'enabled' : 'disabled'}`
    );
    
    // Request notification permission if enabled
    if (this.notificationsEnabled) {
      const granted = await this.browserNotificationService.requestPermission();
      if (granted) {
        this.toastService.success(
          'Notifications Enabled', 
          'You will receive reminders at your preferred time to track your habits'
        );
        // Start the notification scheduler
        this.browserNotificationService.startNotificationScheduler();
      } else {
        this.toastService.warning('Permission Denied', 'Please enable notifications in your browser settings');
        // Stop scheduler if permission denied
        this.browserNotificationService.stopNotificationScheduler();
      }
    } else {
      // Stop scheduler if notifications disabled
      this.browserNotificationService.stopNotificationScheduler();
    }
  }

  async onEmailNotificationsChange() {
    try {
      await this.apiService.updateNotificationPreferences({
        email_notifications_enabled: this.emailNotificationsEnabled
      }).toPromise();
      
      // Haptic feedback on mobile
      if (navigator.vibrate) {
        navigator.vibrate(10);
      }
      
      this.toastService.success(
        'Email Notifications Updated',
        `Email notifications are now ${this.emailNotificationsEnabled ? 'enabled' : 'disabled'}`
      );
    } catch (error: any) {
      console.error('Error updating email notifications:', error);
      this.toastService.error('Error', 'Failed to update email notification preferences');
      // Revert on error
      this.emailNotificationsEnabled = !this.emailNotificationsEnabled;
    }
  }

  async onNotificationTimeChange() {
    try {
      await this.apiService.updateNotificationPreferences({
        notification_time: this.notificationTime
      }).toPromise();
      
      // Haptic feedback on mobile
      if (navigator.vibrate) {
        navigator.vibrate(10);
      }
      
      this.toastService.success('Notification Time Updated', `Emails will be sent at ${this.notificationTime}`);
    } catch (error: any) {
      console.error('Error updating notification time:', error);
      this.toastService.error('Error', 'Failed to update notification time');
    }
  }

  async onNotificationFrequencyChange() {
    try {
      await this.apiService.updateNotificationPreferences({
        notification_frequency: this.notificationFrequency
      }).toPromise();
      
      // Haptic feedback on mobile
      if (navigator.vibrate) {
        navigator.vibrate(10);
      }
      
      const frequencyText = this.notificationFrequency === 'daily' ? 'Daily reminders' :
                           this.notificationFrequency === 'weekly' ? 'Weekly summaries' : 'Daily reminders & weekly summaries';
      this.toastService.success('Notification Frequency Updated', frequencyText);
    } catch (error: any) {
      console.error('Error updating notification frequency:', error);
      this.toastService.error('Error', 'Failed to update notification frequency');
    }
  }

  onThemeChange() {
    // Ensure only light or dark
    if (this.theme !== 'light' && this.theme !== 'dark') {
      this.theme = 'dark';
    }
    
    localStorage.setItem('theme', this.theme);
    // Apply theme immediately
    this.applyTheme(this.theme);
    // Haptic feedback on mobile
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
    // Show feedback
    this.toastService.success('Theme Changed', `Theme set to ${this.theme === 'light' ? 'Light' : 'Dark'}`);
  }

  applyTheme(theme: string) {
    // Only allow light or dark
    if (theme !== 'light' && theme !== 'dark') {
      theme = 'dark';
    }
    
    const body = document.body;
    const html = document.documentElement;
    
    // Remove existing theme classes
    body.classList.remove('theme-dark', 'theme-light');
    html.classList.remove('theme-dark', 'theme-light');
    
    if (theme === 'light') {
      body.classList.add('theme-light');
      html.classList.add('theme-light');
      // Apply light theme variables
      document.documentElement.style.setProperty('--bg-dark', '#f5f5f5');
      document.documentElement.style.setProperty('--bg-card', '#ffffff');
      document.documentElement.style.setProperty('--bg-hover', '#f0f0f0');
      document.documentElement.style.setProperty('--text-primary', '#000000');
      document.documentElement.style.setProperty('--text-secondary', '#666666');
      document.documentElement.style.setProperty('--border-color', '#e0e0e0');
    } else {
      // Dark theme (default)
      body.classList.add('theme-dark');
      html.classList.add('theme-dark');
      // Reset to default dark theme variables
      document.documentElement.style.setProperty('--bg-dark', '#0a0a0a');
      document.documentElement.style.setProperty('--bg-card', '#1a1a1a');
      document.documentElement.style.setProperty('--bg-hover', '#2a2a2a');
      document.documentElement.style.setProperty('--text-primary', '#ffffff');
      document.documentElement.style.setProperty('--text-secondary', '#b0b0b0');
      document.documentElement.style.setProperty('--border-color', '#333333');
    }
  }

  getFormattedDate(dateString?: string): string {
    if (!dateString || dateString === 'null' || dateString === 'undefined' || dateString === 'None') return 'N/A';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'N/A';
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch {
      return 'N/A';
    }
  }
}
