import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService, Stats, BadgesResponse, InsightsResponse, DailyLogs } from '../../services/api';
import { ToastService } from '../../services/toast.service';
import { HabitUpdateService } from '../../services/habit-update.service';
import { Subscription } from 'rxjs';

declare var Chart: any;

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('categoryChart', { static: false }) categoryChartRef!: ElementRef<HTMLCanvasElement>;
  
  isLoading = false;
  stats: Stats | null = null;
  badges: BadgesResponse | null = null;
  insights: InsightsResponse | null = null;
  heatmapData: DailyLogs = {};
  currentDate = new Date();
  categoryChart: any = null;
  private habitUpdateSubscription?: Subscription;

  constructor(
    private apiService: ApiService,
    private toastService: ToastService,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private habitUpdateService: HabitUpdateService
  ) {}

  ngOnInit() {
    this.loadDashboard();
    
    // Subscribe to habit toggle events to refresh heatmap
    this.habitUpdateSubscription = this.habitUpdateService.habitToggled$.subscribe(() => {
      this.loadHeatmap();
      this.loadStats(); // Also refresh stats
    });
  }

  ngAfterViewInit() {
    // Chart will be rendered after data loads
  }

  ngOnDestroy() {
    if (this.categoryChart) {
      this.categoryChart.destroy();
    }
    if (this.habitUpdateSubscription) {
      this.habitUpdateSubscription.unsubscribe();
    }
  }

  async loadDashboard() {
    this.isLoading = true;
    try {
      // Load in parallel for faster performance
      // Load heatmap and stats first (most important), then badges and insights
      await Promise.all([
        this.loadHeatmap(),
        this.loadStats()
      ]);
      
      // Load badges and insights in parallel (less critical, can load after)
      await Promise.all([
        this.loadBadges(),
        this.loadInsights()
      ]);
    } catch (error) {
      console.error('Error loading dashboard:', error);
      this.toastService.error('Error', 'Failed to load dashboard');
    } finally {
      this.isLoading = false;
      this.cdr.detectChanges();
    }
  }

  async loadStats() {
    try {
      this.stats = await this.apiService.getStats().toPromise() || null;
      // Render chart immediately if view is ready, otherwise wait
      if (this.stats && this.categoryChartRef) {
        this.renderCategoryChart();
      } else {
        // Small delay only if view not ready
        setTimeout(() => {
          if (this.stats && this.categoryChartRef) {
            this.renderCategoryChart();
          }
        }, 50); // Reduced from 100ms
      }
    } catch (error: any) {
      console.error('Error loading stats:', error);
      if (error.status === 401) {
        this.toastService.warning('Session Expired', 'Please log in again');
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 300);
      } else if (error.status >= 500) {
        this.toastService.error('Server Error', 'Please try again later');
      }
    }
  }

  async loadBadges() {
    try {
      this.badges = await this.apiService.getBadges().toPromise() || null;
    } catch (error) {
      console.error('Error loading badges:', error);
    }
  }

  async loadInsights() {
    try {
      this.insights = await this.apiService.getInsights().toPromise() || null;
    } catch (error) {
      console.error('Error loading insights:', error);
    }
  }

  async loadHeatmap() {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const startDate = `${year}-${String(month + 1).padStart(2, '0')}-01`;
    const endDate = `${year}-${String(month + 1).padStart(2, '0')}-${daysInMonth}`;

    try {
      this.heatmapData = await this.apiService.getDailyLogs(startDate, endDate).toPromise() || {};
      this.cdr.detectChanges(); // Force UI update
    } catch (error) {
      console.error('Error loading heatmap:', error);
    }
  }

  renderCategoryChart() {
    if (!this.stats || !this.categoryChartRef) return;

    const ctx = this.categoryChartRef.nativeElement.getContext('2d');
    if (!ctx) return;

    if (this.categoryChart) {
      this.categoryChart.destroy();
    }

    this.categoryChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this.stats.categories.map(c => c.category),
        datasets: [{
          label: 'Completed',
          data: this.stats.categories.map(c => c.completed),
          backgroundColor: [
            'rgba(168, 85, 247, 0.8)',
            'rgba(20, 184, 166, 0.8)',
            'rgba(236, 72, 153, 0.8)',
            'rgba(59, 130, 246, 0.8)',
            'rgba(16, 185, 129, 0.8)',
            'rgba(245, 158, 11, 0.8)',
          ],
          borderColor: [
            'rgba(168, 85, 247, 1)',
            'rgba(20, 184, 166, 1)',
            'rgba(236, 72, 153, 1)',
            'rgba(59, 130, 246, 1)',
            'rgba(16, 185, 129, 1)',
            'rgba(245, 158, 11, 1)',
          ],
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              color: '#b0b0b0',
              font: { size: 10 }
            },
            grid: {
              color: '#333333'
            }
          },
          x: {
            ticks: {
              color: '#b0b0b0',
              font: { size: 10 }
            },
            grid: {
              color: '#333333'
            }
          }
        }
      }
    });
  }

  getDaysInMonth(): number {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    return new Date(year, month + 1, 0).getDate();
  }

  getDateString(day: number): string {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  getHeatmapDayClass(habitId: string, day: number): string {
    const dateStr = this.getDateString(day);
    const classes: string[] = ['heatmap-day'];

    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const dayDate = new Date(year, month, day);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const isPastDay = dayDate < today;
    const isToday = dayDate.getTime() === today.getTime();
    const isFutureDay = dayDate > today;

    if (this.heatmapData[dateStr] && this.heatmapData[dateStr][habitId] === true) {
      // Completed
      classes.push('heatmap-completed');
    } else if (this.heatmapData[dateStr] && this.heatmapData[dateStr][habitId] === false) {
      // Explicitly marked as false
      if (isPastDay) {
        // Past day marked as missed
        classes.push('heatmap-missed');
      } else {
        // Today or future day unmarked - show as empty (not tracked yet)
        classes.push('heatmap-empty');
      }
    } else {
      // No log entry
      if (isPastDay) {
        // Past day with no log - missed
        classes.push('heatmap-missed');
      } else {
        // Today or future day with no log - empty
        classes.push('heatmap-empty');
      }
    }

    return classes.join(' ');
  }

  getHeatmapPercentage(habitId: string): { percentage: number; completed: number; total: number } {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const daysInMonth = this.getDaysInMonth();
    const today = new Date();
    const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());

    let completedCount = 0;

    // Count completed days up to today (only count days that have passed)
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = this.getDateString(day);
      const cellDate = new Date(year, month, day);

      // Only count days that have passed (up to today)
      if (cellDate <= todayDate) {
        if (this.heatmapData[dateStr] && this.heatmapData[dateStr][habitId] === true) {
          completedCount++;
        }
      }
    }

    // Use total days in month as denominator (not just days passed)
    const percentage = daysInMonth > 0 ? Math.round((completedCount / daysInMonth) * 100) : 0;
    return { percentage, completed: completedCount, total: daysInMonth };
  }

  getHabitsForHeatmap() {
    return this.stats?.habits || [];
  }

  getDaysArray(): number[] {
    const days: number[] = [];
    const daysInMonth = this.getDaysInMonth();
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(day);
    }
    return days;
  }
}
