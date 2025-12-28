import { Injectable } from '@angular/core';
import { AuthService } from './auth';

@Injectable({
  providedIn: 'root'
})
export class SyncService {
  private lastSyncTime: number = 0;
  private syncDebounceMs = 2000; // 2 seconds debounce for automatic syncs

  constructor(private authService: AuthService) {}

  /**
   * Trigger a sync after user action (debounced)
   * This is called automatically when user makes changes
   */
  syncAfterAction(): void {
    const now = Date.now();
    
    // Debounce: Don't sync if last sync was less than 2 seconds ago
    if (now - this.lastSyncTime < this.syncDebounceMs) {
      return;
    }
    
    this.lastSyncTime = now;
    
    // Update auth status (silent sync)
    // Components will handle their own data reloading
    this.authService.checkAuth();
  }

  /**
   * Force immediate sync (for manual sync button)
   */
  forceSync(): void {
    this.lastSyncTime = Date.now();
    this.authService.checkAuth();
  }
}

