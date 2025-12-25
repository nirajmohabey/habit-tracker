import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './forgot-password.html',
  styleUrl: './forgot-password.css'
})
export class ForgotPasswordComponent {
  emailOrUsername = '';
  error = '';
  success = false;
  isLoading = false;

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  onSubmit() {
    this.error = '';
    this.isLoading = true;

    if (!this.emailOrUsername.trim()) {
      this.error = 'Please enter your email or username';
      this.isLoading = false;
      return;
    }

    const AUTH_URL = environment.apiUrl.replace('/api', '');
    const input = this.emailOrUsername.trim();
    
    // Determine if input is email or username
    const isEmail = input.includes('@');
    
    // Build request body without undefined values
    const requestBody: any = {};
    if (isEmail) {
      requestBody.email = input;
    } else {
      requestBody.username = input;
    }
    
    this.http.post(`${AUTH_URL}/forgot-password`, requestBody, { 
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json'
      }
    }).subscribe({
      next: (response: any) => {
        this.isLoading = false;
        this.success = true;
      },
      error: (err) => {
        console.error('Forgot password error:', err);
        this.isLoading = false;
        this.error = err.error?.error || err.message || 'Failed to send password reset. Please try again.';
      }
    });
  }
}

