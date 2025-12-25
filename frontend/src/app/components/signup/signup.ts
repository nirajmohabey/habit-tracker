import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './signup.html',
  styleUrl: './signup.css'
})
export class SignupComponent {
  username = '';
  email = '';
  password = '';
  confirmPassword = '';
  error = '';
  requiresOTP = false;
  otp = '';
  isLoading = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {
    // Redirect if already authenticated
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/tracker']);
    }
  }

  onSubmit() {
    this.error = '';
    
    if (this.requiresOTP) {
      // Verify OTP
      this.verifyOTP();
      return;
    }
    
    if (this.password !== this.confirmPassword) {
      this.error = 'Passwords do not match';
      return;
    }
    
    if (this.password.length < 6) {
      this.error = 'Password must be at least 6 characters';
      return;
    }
    
    this.isLoading = true;
    this.authService.signup(this.username, this.email, this.password, this.confirmPassword).subscribe({
      next: (response: any) => {
        this.isLoading = false;
        if (response.requires_verification) {
          // OTP required
          this.requiresOTP = true;
        } else {
          // Direct signup (no email)
        this.router.navigate(['/tracker']);
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.error = err.error?.error || 'Signup failed. Please try again.';
      }
    });
  }
  
  verifyOTP() {
    this.error = '';
    this.isLoading = true;
    
    if (!this.otp || this.otp.length !== 6) {
      this.error = 'Please enter a valid 6-digit OTP code';
      this.isLoading = false;
      return;
    }
    
    this.authService.verifyOTP(this.email, this.otp).subscribe({
      next: () => {
        this.isLoading = false;
        this.router.navigate(['/tracker']);
      },
      error: (err) => {
        this.isLoading = false;
        this.error = err.error?.error || 'Invalid OTP code. Please try again.';
      }
    });
  }
}
