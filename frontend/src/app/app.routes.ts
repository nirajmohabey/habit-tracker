import { Routes } from '@angular/router';
import { LoginComponent } from './components/login/login';
import { SignupComponent } from './components/signup/signup';
import { DailyTracker } from './components/daily-tracker/daily-tracker';
import { Dashboard } from './components/dashboard/dashboard';
import { Settings } from './components/settings/settings';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from './services/auth';
import { map, take, timeout, catchError, filter } from 'rxjs/operators';
import { of, race, timer } from 'rxjs';

// Auth guard - improved to handle async auth state on page reload
const authGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  
  // First check if user is already authenticated (from previous session)
  const currentUser = authService.getCurrentUser();
  if (currentUser) {
    return of(true); // User already authenticated, allow access immediately
  }
  
  // User not in memory - trigger auth check
  authService.checkAuth();
  
  // Wait for auth check to complete - optimized for speed
  // Race between: waiting for user to be set, or a short timeout
  return race(
    // Option 1: Wait for user to be authenticated
    authService.currentUser$.pipe(
      filter(user => user !== null), // Wait for non-null user
      take(1),
      map(() => true)
    ),
    // Option 2: After 500ms, check if auth check completed (even if user is null)
    timer(500).pipe(
      map(() => {
        // Check if user is authenticated after waiting
        const user = authService.getCurrentUser();
        if (user) {
          return true;
        }
        // User is not authenticated - redirect to login
        router.navigate(['/login']);
        return false;
      })
    )
  ).pipe(
    take(1),
    timeout(1500), // Overall 1.5 second timeout (reduced from 3s)
    catchError(() => {
      // Final check on error
      const user = authService.getCurrentUser();
      if (user) {
        return of(true);
      }
      router.navigate(['/login']);
      return of(false);
    })
  );
};

import { ForgotPasswordComponent } from './components/forgot-password/forgot-password';

export const routes: Routes = [
  { path: '', redirectTo: '/tracker', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'signup', component: SignupComponent },
  { path: 'forgot-password', component: ForgotPasswordComponent },
  { 
    path: 'tracker', 
    component: DailyTracker,
    canActivate: [authGuard]
  },
  { 
    path: 'dashboard', 
    component: Dashboard,
    canActivate: [authGuard]
  },
  { 
    path: 'settings', 
    component: Settings,
    canActivate: [authGuard]
  },
  { path: '**', redirectTo: '/tracker' }
];
