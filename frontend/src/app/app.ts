import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { RouterOutlet, RouterModule, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService, User } from './services/auth';
import { ApiService } from './services/api';
import { ToastService } from './services/toast.service';
import { BrowserNotificationService } from './services/browser-notification.service';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterModule, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit, OnDestroy {
  currentUser$: Observable<User | null>;
  currentTab = 'tracker';
  isAuthenticated = false;
  authCheckInProgress = true; // Track if auth check is in progress
  dropdownOpen = false;
  syncStatus: 'synced' | 'syncing' | 'error' = 'synced';
  private syncInterval: any = null;
  private isSyncing = false;
  private manualSync = false; // Track if sync was manually triggered

  constructor(
    public authService: AuthService,
    private router: Router,
    private apiService: ApiService,
    private toastService: ToastService,
    private browserNotificationService: BrowserNotificationService
  ) {
    // Initialize currentUser$ after constructor
    this.currentUser$ = this.authService.currentUser$;
  }

  ngOnInit() {
    // Apply saved theme immediately on app load
    this.applyThemeOnInit();
    
    // Check auth on init
    this.authService.checkAuth();
    
    // Subscribe to auth state
    this.authService.currentUser$.subscribe(user => {
      const wasAuthenticated = this.isAuthenticated;
      this.isAuthenticated = user !== null;
      this.authCheckInProgress = false; // Auth check completed
      
      if (this.isAuthenticated && !wasAuthenticated) {
        // First time authentication - show welcome message
        setTimeout(() => {
          this.toastService.success('Welcome back!', 'Your habits are synced across all devices');
        }, 100); // Reduced to 100ms
        this.setupRealTimeSync();
        this.setupPullToRefresh();
        // Start browser notification scheduler
        this.browserNotificationService.startNotificationScheduler();
      }
      
      // Stop notifications if user logs out
      if (!this.isAuthenticated && wasAuthenticated) {
        this.browserNotificationService.stopNotificationScheduler();
      }
      
      // If user becomes unauthenticated while on protected route, redirect
      if (!this.isAuthenticated && wasAuthenticated) {
        const currentUrl = this.router.url;
        if (currentUrl !== '/login' && currentUrl !== '/signup') {
          this.router.navigate(['/login']);
        }
      }
    });
    
    // Set timeout to stop showing loading if auth check takes too long
    setTimeout(() => {
      if (this.authCheckInProgress) {
        this.authCheckInProgress = false;
      }
    }, 1500); // Reduced to 1.5 seconds for faster loading
    
    // Watch route changes to update active tab
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: any) => {
      const url = event.url;
      if (url.includes('/tracker')) this.currentTab = 'tracker';
      else if (url.includes('/dashboard')) this.currentTab = 'dashboard';
      else if (url.includes('/settings')) this.currentTab = 'settings';
    });
  }

  ngOnDestroy() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
    }
    // Stop notification scheduler
    this.browserNotificationService.stopNotificationScheduler();
  }

  private applyThemeOnInit() {
    // Load theme from localStorage and apply immediately
    const savedTheme = localStorage.getItem('theme');
    const theme = (savedTheme === 'light' || savedTheme === 'dark') ? savedTheme : 'dark';
    
    // Ensure theme is saved if it wasn't set
    if (!savedTheme || (savedTheme !== 'light' && savedTheme !== 'dark')) {
      localStorage.setItem('theme', 'dark');
    }
    
    // Apply theme immediately
    this.applyTheme(theme);
  }

  private applyTheme(theme: string) {
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

  toggleDropdown(event: Event) {
    event.stopPropagation();
    this.dropdownOpen = !this.dropdownOpen;
  }

  @HostListener('document:click', ['$event'])
  closeDropdownOnOutsideClick(event: Event) {
    const target = event.target as HTMLElement;
    const dropdown = document.getElementById('userDropdown');
    if (dropdown && !dropdown.contains(target)) {
      this.dropdownOpen = false;
    }
  }

  async syncData(manual: boolean = false) {
    if (this.isSyncing) return;
    
    this.manualSync = manual; // Track if this is a manual sync
    this.isSyncing = true;
    this.syncStatus = 'syncing';
    this.dropdownOpen = false;
    
    try {
      // Just update auth status - components will handle their own data reloading
      // No need to navigate and cause full page reloads
      this.authService.checkAuth();
      
      this.syncStatus = 'synced';
      // Only show toast on manual sync (user clicked sync button or pull-to-refresh)
      if (manual) {
        this.toastService.success('Synced', 'Your data has been updated');
      }
    } catch (error) {
      console.error('Sync error:', error);
      this.syncStatus = 'error';
      if (manual) {
        this.toastService.error('Sync Failed', 'Could not sync data. Check your connection.');
      }
    } finally {
      this.isSyncing = false;
      this.manualSync = false;
    }
  }

  setupRealTimeSync() {
    // Clear existing interval
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
    }

    // Sync every 30 seconds (reduced frequency to avoid too many requests)
    this.syncInterval = setInterval(() => {
      if (!this.isSyncing && this.isAuthenticated) {
        this.syncData(false); // Silent background sync
      }
    }, 30000); // Changed from 10 seconds to 30 seconds
  }

  @HostListener('window:visibilitychange')
  onVisibilityChange() {
    if (!document.hidden && !this.isSyncing && this.isAuthenticated) {
      // Silent sync when tab becomes visible
      this.syncData(false);
    }
  }

  @HostListener('window:focus')
  onWindowFocus() {
    if (!this.isSyncing && this.isAuthenticated) {
      // Silent sync when window regains focus
      this.syncData(false);
    }
  }

  setupPullToRefresh() {
    let touchStartY = 0;
    let touchCurrentY = 0;
    let pullRefreshActive = false;
    const threshold = 80;
    const pullRefresh = document.getElementById('pull-refresh');
    
    if (!pullRefresh) return;

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
        await this.syncData(true); // Manual sync from pull-to-refresh
      }
      
      pullRefresh.style.top = '-60px';
      pullRefresh.classList.remove('active');
      pullRefreshActive = false;
      touchStartY = 0;
      touchCurrentY = 0;
    }, { passive: true });
  }

  navigateTo(tab: string) {
    this.currentTab = tab;
    this.router.navigate([`/${tab}`]);
    
    // Manage body classes for dashboard
    if (tab === 'dashboard') {
      document.body.classList.add('dashboard-active');
      document.documentElement.classList.add('dashboard-active');
    } else {
      document.body.classList.remove('dashboard-active');
      document.documentElement.classList.remove('dashboard-active');
    }
  }

  logout() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
    }
    this.authService.logout().subscribe(() => {
      this.router.navigate(['/login']);
    });
  }
}
