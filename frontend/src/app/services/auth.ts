import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

// Auth endpoints: /login, /signup, /logout are NOT under /api
// But /api/check-auth IS under /api
const AUTH_URL = environment.apiUrl.replace('/api', ''); // Remove /api for login/signup/logout
const API_URL = environment.apiUrl; // Keep /api for check-auth

export interface User {
  id: string;
  username: string;
  email?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    this.checkAuth();
  }

  checkAuth(): void {
    this.http.get<any>(`${API_URL}/check-auth`, { withCredentials: true }).subscribe({
      next: (response) => {
        if (response.authenticated && response.user) {
          // Ensure email is included in user object
          const user: User = {
            id: response.user.id,
            username: response.user.username,
            email: response.user.email
          };
          this.currentUserSubject.next(user);
        } else {
          this.currentUserSubject.next(null);
        }
      },
      error: (err) => {
        console.error('Auth check failed:', err);
        // Set user to null on error (not authenticated)
        this.currentUserSubject.next(null);
      }
    });
  }

  login(username: string, password: string): Observable<any> {
    return this.http.post(`${AUTH_URL}/login`, {
      username,
      password
    }, { withCredentials: true }).pipe(
      tap((response: any) => {
        if (response.user) {
          // Ensure email is included
          const user: User = {
            id: response.user.id,
            username: response.user.username,
            email: response.user.email
          };
          this.currentUserSubject.next(user);
          // No need to re-check auth immediately - we already have user from response
          // Only check if session might not be established (rare case)
        }
      })
    );
  }

  signup(username: string, email: string, password: string, confirmPassword: string): Observable<any> {
    return this.http.post(`${AUTH_URL}/signup`, {
      username,
      email,
      password,
      confirm_password: confirmPassword
    }, { withCredentials: true }).pipe(
      tap((response: any) => {
        if (response.user && !response.requires_verification) {
          this.currentUserSubject.next(response.user);
        }
      })
    );
  }
  
  verifyOTP(email: string, otp: string): Observable<any> {
    return this.http.post(`${AUTH_URL}/verify-otp`, {
      email,
      otp
    }, { withCredentials: true }).pipe(
      tap((response: any) => {
        if (response.user) {
          // Ensure email is included
          const user: User = {
            id: response.user.id,
            username: response.user.username,
            email: response.user.email
          };
          this.currentUserSubject.next(user);
          // No need to re-check auth - we already have user from response
        }
      })
    );
  }

  logout(): Observable<any> {
    return this.http.get(`${AUTH_URL}/logout`, { withCredentials: true }).pipe(
      tap(() => {
        this.currentUserSubject.next(null);
      })
    );
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  isAuthenticated(): boolean {
    return this.currentUserSubject.value !== null;
  }
}
