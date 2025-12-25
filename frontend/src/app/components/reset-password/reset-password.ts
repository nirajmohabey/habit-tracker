import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './reset-password.html',
  styleUrl: './reset-password.css'
})
export class ResetPasswordComponent implements OnInit {
  token = '';
  password = '';
  confirmPassword = '';
  error = '';
  success = false;
  isLoading = false;
  tokenValid = false;
  checkingToken = true;

  constructor(
    private http: HttpClient,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    // Get token from query parameter
    this.route.queryParams.subscribe(params => {
      this.token = params['token'] || '';
      if (this.token) {
        this.verifyToken();
      } else {
        this.checkingToken = false;
        this.error = 'Invalid reset link. Please request a new password reset.';
      }
    });
  }

  verifyToken() {
    this.checkingToken = true;
    const API_URL = environment.apiUrl;
    
    this.http.post(`${API_URL}/verify-reset-token`, { token: this.token }, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json'
      }
    }).subscribe({
      next: (response: any) => {
        this.checkingToken = false;
        if (response.valid) {
          this.tokenValid = true;
        } else {
          this.error = 'Invalid or expired reset token. Please request a new password reset.';
        }
      },
      error: (err) => {
        this.checkingToken = false;
        this.error = err.error?.error || 'Invalid or expired reset token. Please request a new password reset.';
      }
    });
  }

  onSubmit() {
    this.error = '';
    
    if (!this.password || !this.confirmPassword) {
      this.error = 'Please fill in all fields';
      return;
    }

    if (this.password.length < 6) {
      this.error = 'Password must be at least 6 characters long';
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.error = 'Passwords do not match';
      return;
    }

    this.isLoading = true;
    const API_URL = environment.apiUrl;
    
    this.http.post(`${API_URL}/reset-password`, {
      token: this.token,
      password: this.password,
      confirm_password: this.confirmPassword
    }, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json'
      }
    }).subscribe({
      next: (response: any) => {
        this.isLoading = false;
        this.success = true;
        // Redirect to login after 2 seconds
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 2000);
      },
      error: (err) => {
        this.isLoading = false;
        this.error = err.error?.error || 'Failed to reset password. Please try again.';
      }
    });
  }
}

