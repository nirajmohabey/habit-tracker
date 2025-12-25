import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class LoginComponent {
  username = '';
  password = '';
  error = '';

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
    this.authService.login(this.username, this.password).subscribe({
      next: (response) => {
        // Wait a moment for session to be established
        setTimeout(() => {
          // Verify auth before navigating
          if (this.authService.isAuthenticated()) {
            this.router.navigate(['/tracker']);
          } else {
            // If auth check fails, try one more time
            this.authService.checkAuth();
            setTimeout(() => {
              if (this.authService.isAuthenticated()) {
                this.router.navigate(['/tracker']);
              } else {
                this.error = 'Login successful but session not established. Please try again.';
              }
            }, 500);
          }
        }, 200);
      },
      error: (err) => {
        this.error = err.error?.error || 'Login failed. Please check your credentials.';
      }
    });
  }
}
