import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, Habit, DailyLogs } from '../../services/api';
import { ToastService } from '../../services/toast.service';
import { AuthService } from '../../services/auth';
import { AutoMarkService } from '../../services/auto-mark.service';
import { HabitUpdateService } from '../../services/habit-update.service';
import { Subscription } from 'rxjs';

interface WeekGroup {
  sundayDay: number;
  startDay: number;
  endDay: number;
  days: number[];
}

@Component({
  selector: 'app-daily-tracker',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './daily-tracker.html',
  styleUrl: './daily-tracker.css',
})
export class DailyTracker implements OnInit, OnDestroy {
  habits: Habit[] = [];
  dailyLogs: DailyLogs = {};
  currentDate = new Date(2025, 11, 1); // December 2025
  userStartDate: Date | null = null;
  isLoading = false;
  showAddModal = false;
  editingHabitId: string | null = null;
  private autoMarkSubscription?: Subscription;
  editingInline: { [habitId: string]: { name: string; goal: number } } = {};
  
  // Form data
  habitForm = {
    name: '',
    emoji: '✅',
    category: 'Fitness',
    customCategory: '',
    goal: 31 // Hidden from user, auto-set to days in month
  };
  
  // Common emojis for picker
  commonEmojis = [
    '✅', '💪', '🏃', '🧘', '📚', '💧', '🍎', '😴', 
    '🎯', '🔥', '⭐', '💯', '🎨', '🎵', '📝', '💰',
    '🏋️', '🚶', '🧠', '❤️', '🌱', '🎪', '🏆', '🌟'
  ];

  readonly MIN_DATE = new Date(2025, 11, 1); // December 1, 2025
  readonly monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

  constructor(
    private apiService: ApiService,
    private toastService: ToastService,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private autoMarkService: AutoMarkService,
    private habitUpdateService: HabitUpdateService
  ) {}

  ngOnInit() {
    // Load habits first (it will also get user start date from checkAuth)
    this.loadHabits();
    
    // Subscribe to auto-mark trigger from settings
    this.autoMarkSubscription = this.autoMarkService.onAutoMarkRequested.subscribe(() => {
      // When triggered from settings, show feedback
      this.autoMarkMissedDaysIfNeeded(true);
    });
  }

  ngOnDestroy() {
    if (this.autoMarkSubscription) {
      this.autoMarkSubscription.unsubscribe();
    }
  }

  async loadUserStartDate() {
    try {
      const response = await this.apiService.checkAuth().toPromise();
      if (response && response.start_date) {
        this.userStartDate = new Date(response.start_date);
      }
    } catch (error) {
      // Silently fail - not critical
    }
  }

  async loadHabits() {
    this.isLoading = true;
    try {
      // Check if still authenticated before making API call
      if (!this.authService.isAuthenticated()) {
        this.router.navigate(['/login']);
        return;
      }

      // Load habits and user start date in parallel for faster loading
      const [habitsResponse, authResponse] = await Promise.all([
        this.apiService.getHabits().toPromise().catch(() => []),
        this.apiService.checkAuth().toPromise().catch(() => null)
      ]);
      
      this.habits = habitsResponse || [];
      
      // Load user start date from auth response
      if (authResponse && authResponse.start_date) {
        this.userStartDate = new Date(authResponse.start_date);
      }
      
      // Retry if no habits found (backend might be creating defaults) - but faster
      if (this.habits.length === 0) {
        await new Promise(resolve => setTimeout(resolve, 200)); // Reduced to 200ms
        this.habits = await this.apiService.getHabits().toPromise() || [];
      }
      
      // Show data immediately after habits are loaded
      this.cdr.detectChanges();
      
      // Load daily logs first
      await this.loadDailyLogs();
      
      // Show UI immediately
      this.cdr.detectChanges();
      
      // Run auto-mark in background (non-blocking) after UI is shown
      this.autoMarkMissedDaysIfNeeded(false)
        .then(() => {
          // Reload logs after auto-mark completes to show updated state
          this.loadDailyLogs().then(() => {
            this.cdr.detectChanges();
          });
        })
        .catch((error) => {
          console.error('Auto-mark failed on initial load:', error);
          // Silently fail - not critical for initial load
        });
    } catch (error: any) {
      console.error('Error loading habits:', error);
      if (error.status === 401 || error.status === 0) {
        // 401 = Unauthorized, 0 = Network error (backend down)
        this.authService.checkAuth();
        await new Promise(resolve => setTimeout(resolve, 100)); // Reduced to 100ms
        if (!this.authService.isAuthenticated()) {
          this.toastService.warning('Session Expired', 'Please log in again');
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 300); // Reduced to 300ms
        } else {
          // Auth is fine, retry loading habits
          this.loadHabits();
        }
      } else {
        this.toastService.error('Error', 'Failed to load habits. Please refresh the page.');
        this.isLoading = false;
      }
    } finally {
      this.isLoading = false;
    }
  }

  // Separate method for auto-marking (non-blocking)
  async autoMarkMissedDaysIfNeeded(showFeedback = false) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const viewingYear = this.currentDate.getFullYear();
    const viewingMonth = this.currentDate.getMonth();
    const viewingDate = new Date(viewingYear, viewingMonth, 1);
    viewingDate.setHours(0, 0, 0, 0);
    
    const savedAutoMark = localStorage.getItem('autoMarkMissed');
    const autoMarkEnabled = savedAutoMark === null || savedAutoMark === 'true';
    
    if (!autoMarkEnabled) {
      return;
    }
    
    const isPastMonth = viewingDate < today;
    const isCurrentMonth = viewingYear === today.getFullYear() && viewingMonth === today.getMonth();
    
    if (isPastMonth || isCurrentMonth) {
      if (showFeedback) {
        this.isLoading = true;
        this.cdr.detectChanges();
      }
      
      try {
        const result = await this.autoMarkMissedDays(viewingYear, viewingMonth);
        
        // Reload logs after auto-mark completes (only if feedback is requested or result has marked days)
        if (showFeedback || (result && result.marked_count > 0)) {
          await this.loadDailyLogs();
          this.cdr.detectChanges();
        }
        
        if (showFeedback) {
          const count = result?.marked_count || 0;
          if (count > 0) {
            this.toastService.success('Auto-marked', `${count} past days have been marked as missed`);
          } else {
            this.toastService.info('Auto-marked', 'All past days are already marked');
          }
        }
      } catch (error) {
        console.error('Auto-mark error:', error);
        if (showFeedback) {
          this.toastService.error('Error', 'Failed to auto-mark missed days');
        }
      } finally {
        if (showFeedback) {
          this.isLoading = false;
          this.cdr.detectChanges();
        }
        }
      } else if (showFeedback) {
      this.toastService.info('No past days', 'There are no past days to mark in this month');
    }
  }

  async loadDailyLogs() {
    if (!this.habits || this.habits.length === 0) return;

    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const startDate = `${year}-${String(month + 1).padStart(2, '0')}-01`;
    
    let nextMonth = month + 1;
    let nextYear = year;
    if (nextMonth > 11) {
      nextMonth = 0;
      nextYear = year + 1;
    }
    const endDate = `${nextYear}-${String(nextMonth + 1).padStart(2, '0')}-01`;

    try {
      const logs = await this.apiService.getDailyLogs(startDate, endDate).toPromise() || {};
      // Filter to only include dates within the current month
      this.dailyLogs = {};
      Object.keys(logs).forEach(dateStr => {
        const logDate = new Date(dateStr);
        if (logDate.getFullYear() === year && logDate.getMonth() === month) {
          this.dailyLogs[dateStr] = logs[dateStr];
        }
      });
    } catch (error) {
      console.error('Error loading daily logs:', error);
      this.toastService.error('Error', 'Failed to load daily logs');
    }
  }

  getCurrentMonthYear(): string {
    return `${this.monthNames[this.currentDate.getMonth()]} ${this.currentDate.getFullYear()}`;
  }

  canGoPrevious(): boolean {
    const currentMonthStart = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
    const minMonthStart = new Date(this.MIN_DATE.getFullYear(), this.MIN_DATE.getMonth(), 1);
    return currentMonthStart > minMonthStart;
  }

  async previousMonth() {
    if (!this.canGoPrevious()) {
      this.toastService.info('Cannot go back', 'Calendar starts from December 2025');
      return;
    }

    const newDate = new Date(this.currentDate);
    newDate.setMonth(newDate.getMonth() - 1);
    this.currentDate = newDate;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const viewingDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
    viewingDate.setHours(0, 0, 0, 0);

    this.dailyLogs = {};

    // Check if auto-mark is enabled
    const savedAutoMark = localStorage.getItem('autoMarkMissed');
    const autoMarkEnabled = savedAutoMark === null || savedAutoMark === 'true';
    
    // Run auto-mark for past months OR past days in current month
    if (autoMarkEnabled && (viewingDate < today || (viewingDate.getMonth() === today.getMonth() && viewingDate.getFullYear() === today.getFullYear()))) {
      // Run auto-mark in background
      this.autoMarkMissedDays(this.currentDate.getFullYear(), this.currentDate.getMonth())
        .then(() => {
          this.loadDailyLogs().then(() => this.cdr.detectChanges());
        })
        .catch(() => {});
    }

    await this.loadDailyLogs();
    this.cdr.detectChanges();
  }

  async nextMonth() {
    const newDate = new Date(this.currentDate);
    newDate.setMonth(newDate.getMonth() + 1);
    this.currentDate = newDate;

    this.dailyLogs = {};
    await this.loadDailyLogs();
    this.cdr.detectChanges();
  }

  getDaysInMonth(): number {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    return new Date(year, month + 1, 0).getDate();
  }

  getStartDay(): number {
    let startDay = 1;
    if (this.userStartDate) {
      const year = this.currentDate.getFullYear();
      const month = this.currentDate.getMonth();
      const startDate = new Date(this.userStartDate);
      if (startDate.getFullYear() === year && startDate.getMonth() === month) {
        startDay = startDate.getDate();
      }
    }
    return startDay;
  }

  getWeekGroups(): WeekGroup[] {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const daysInMonth = this.getDaysInMonth();
    const startDay = this.getStartDay();

    const weekGroups: WeekGroup[] = [];
    let currentWeek: WeekGroup | null = null;

    for (let day = startDay; day <= daysInMonth; day++) {
      const dayDate = new Date(year, month, day);
      const dayOfWeek = dayDate.getDay();
      const daysFromSunday = dayOfWeek;
      const weekSunday = day - daysFromSunday;

      if (dayOfWeek === 0 || currentWeek === null || weekSunday !== currentWeek.sundayDay) {
        currentWeek = {
          sundayDay: weekSunday,
          startDay: day,
          endDay: day,
          days: [day]
        };
        weekGroups.push(currentWeek);
      } else {
        currentWeek.days.push(day);
        currentWeek.endDay = day;
      }
    }

    return weekGroups;
  }

  getDateString(day: number): string {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  isDayCompleted(habitId: string, day: number): boolean {
    const dateStr = this.getDateString(day);
    return !!(this.dailyLogs[dateStr] && this.dailyLogs[dateStr][habitId] === true);
  }

  isDayMissed(habitId: string, day: number): boolean {
    const dateStr = this.getDateString(day);
    return !!(this.dailyLogs[dateStr] && this.dailyLogs[dateStr][habitId] === false);
  }

  isPastDay(day: number): boolean {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const dayDate = new Date(year, month, day);
    dayDate.setHours(0, 0, 0, 0);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return dayDate < today;
  }

  isToday(day: number): boolean {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const dayDate = new Date(year, month, day);
    dayDate.setHours(0, 0, 0, 0);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return dayDate.getTime() === today.getTime();
  }

  isDayDisabled(habitId: string, day: number): boolean {
    // Past days (not today) that are not completed should be disabled
    if (this.isPastDay(day) && !this.isToday(day)) {
      // If it's completed, allow interaction
      if (this.isDayCompleted(habitId, day)) {
        return false;
      }
      // Otherwise, disable it (it's either missed or not logged)
      return true;
    }
    return false;
  }

  onDayCheckboxChange(habitId: string, day: number, checkbox: HTMLInputElement) {
    // Don't allow toggling disabled (past) days
    if (checkbox.disabled) {
      checkbox.checked = false; // Reset to unchecked
      return;
    }
    this.toggleHabitLog(habitId, day, checkbox.checked);
  }

  async toggleHabitLog(habitId: string, day: number, completed: boolean) {
    const dateStr = this.getDateString(day);
    
    if (this.isDayDisabled(habitId, day)) {
      this.toastService.error('Cannot Change Past Day', 'Past days marked as missed are locked');
      await this.loadDailyLogs();
      this.cdr.detectChanges();
      return;
    }

    // Optimistically update UI immediately (before API call)
    if (!this.dailyLogs[dateStr]) {
      this.dailyLogs[dateStr] = {};
    }
    const previousState = this.dailyLogs[dateStr][habitId];
    this.dailyLogs[dateStr][habitId] = completed;
    this.cdr.detectChanges(); // Force immediate UI update

    try {
      // Make API call in background
      await this.apiService.toggleLog(habitId, dateStr, completed).toPromise();
      
      const habit = this.habits.find(h => h.id === habitId);
      if (completed && habit) {
        this.toastService.success('Habit Completed!', `${habit.name} marked as done`);
      }
      
      // Notify other components (like dashboard) that a habit was toggled
      this.habitUpdateService.notifyHabitToggled();
    } catch (error: any) {
      console.error('Error toggling habit log:', error);
      
      // Revert optimistic update on error
      if (previousState !== undefined) {
        this.dailyLogs[dateStr][habitId] = previousState;
      } else {
        delete this.dailyLogs[dateStr][habitId];
      }
      this.cdr.detectChanges();
      
      if (error.status === 403) {
        this.toastService.error('Cannot Change Past Day', error.error?.error || 'Past days marked as missed are locked');
      } else {
        this.toastService.error('Error', 'Failed to update habit');
      }
    }
  }

  async autoMarkMissedDays(year: number, month: number) {
    try {
      // month is 0-11 from JavaScript Date, convert to 1-12 for backend
      const backendMonth = month + 1;
      const result = await this.apiService.autoMarkMissedDays(year, backendMonth).toPromise();
      
      return result;
    } catch (error: any) {
      console.error('Error in autoMarkMissedDays:', error);
      throw error; // Re-throw so calling function can handle it
    }
  }

  openAddModal() {
    this.editingHabitId = null;
    this.habitForm = {
      name: '',
      emoji: '✅',
      category: 'Fitness',
      customCategory: '',
      goal: this.getDaysInMonth() // Auto-set to days in current month
    };
    this.showAddModal = true;
  }
  
  selectEmoji(emoji: string) {
    this.habitForm.emoji = emoji;
  }

  closeModal() {
    this.showAddModal = false;
    this.editingHabitId = null;
  }

  async saveHabit() {
    if (!this.habitForm.name.trim()) {
      this.toastService.error('Error', 'Habit name cannot be empty');
      return;
    }
    
    // Use custom category if "Other" is selected and custom category is provided
    const category = this.habitForm.category === 'Other' && this.habitForm.customCategory.trim() 
      ? this.habitForm.customCategory.trim() 
      : this.habitForm.category;
    
    // Prepare habit data (goal is auto-set to days in month, hidden from user)
    const habitData = {
      name: this.habitForm.name.trim(),
      emoji: this.habitForm.emoji || '✅',
      category: category,
      goal: this.getDaysInMonth() // Auto-set to days in current month
    };

    try {
      if (this.editingHabitId) {
        await this.apiService.updateHabit(this.editingHabitId, habitData).toPromise();
        this.toastService.success('Habit Updated', `${habitData.name} has been updated`);
      } else {
        await this.apiService.createHabit(habitData).toPromise();
        this.toastService.success('Habit Added', `${habitData.name} has been added to your tracker`);
      }

      this.closeModal();
      await this.loadHabits();
      this.cdr.detectChanges();
    } catch (error) {
      console.error('Error saving habit:', error);
      this.toastService.error('Error', `Failed to ${this.editingHabitId ? 'update' : 'add'} habit`);
    }
  }

  async deleteHabit(habitId: string) {
    const habit = this.habits.find(h => h.id === habitId);
    const habitName = habit ? habit.name : 'Habit';

    if (!confirm(`Are you sure you want to delete "${habitName}"? This will also delete all associated logs.`)) {
      return;
    }

    try {
      await this.apiService.deleteHabit(habitId).toPromise();
      this.toastService.success('Habit Deleted', `${habitName} has been removed`);
      await this.loadHabits();
      this.cdr.detectChanges();
    } catch (error: any) {
      console.error('Error deleting habit:', error);
      this.toastService.error('Error', error.error?.error || 'Failed to delete habit');
    }
  }

  editHabitInline(habitId: string) {
    const habit = this.habits.find(h => h.id === habitId);
    if (!habit) return;

    // Start inline editing
    this.editingInline[habitId] = {
      name: habit.name,
      goal: habit.goal
    };
    this.cdr.detectChanges();
    
    // Focus the name input after view update
    setTimeout(() => {
      const nameInput = document.querySelector(`input[data-habit-id="${habitId}"][data-field="name"]`) as HTMLInputElement;
      if (nameInput) {
        nameInput.focus();
        nameInput.select();
      }
    }, 0);
  }

  isEditingInline(habitId: string): boolean {
    return !!this.editingInline[habitId];
  }

  getEditingName(habitId: string): string {
    return this.editingInline[habitId]?.name || '';
  }

  async saveInlineEdit(habitId: string) {
    const editData = this.editingInline[habitId];
    if (!editData) return;

    const newName = editData.name.trim();

    if (!newName) {
      this.cancelInlineEdit(habitId);
      this.toastService.error('Error', 'Habit name cannot be empty');
      return;
    }

    const habit = this.habits.find(h => h.id === habitId);
    if (!habit) {
      this.cancelInlineEdit(habitId);
      return;
    }

    if (newName === habit.name) {
      // No changes, just cancel
      this.cancelInlineEdit(habitId);
      return;
    }

    try {
      await this.apiService.updateHabit(habitId, {
        name: newName
        // Goal is not editable by user, keep existing value
      }).toPromise();

      this.toastService.success('Habit Updated', `${newName} has been updated`);
      await this.loadHabits();
      this.cdr.detectChanges();
    } catch (error: any) {
      console.error('Error updating habit inline:', error);
      this.toastService.error('Error', 'Failed to update habit');
      this.cancelInlineEdit(habitId);
    }
  }

  cancelInlineEdit(habitId: string) {
    delete this.editingInline[habitId];
    this.cdr.detectChanges();
  }

  onInlineNameChange(habitId: string, value: string) {
    if (this.editingInline[habitId]) {
      this.editingInline[habitId].name = value;
    }
  }

  onInlineKeyDown(habitId: string, event: KeyboardEvent, field: 'name') {
    if (event.key === 'Enter') {
      event.preventDefault();
      this.saveInlineEdit(habitId);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      this.cancelInlineEdit(habitId);
    }
  }

  getDayClass(habitId: string, day: number): string {
    const classes: string[] = ['day-cell'];
    
    const isCompleted = this.isDayCompleted(habitId, day);
    const isPast = this.isPastDay(day);
    const isToday = this.isToday(day);
    const isMissed = this.isDayMissed(habitId, day);
    
    if (isCompleted) {
      classes.push('day-completed');
    } else if (isToday) {
      classes.push('day-today');
    } else if (isPast && !isToday) {
      // Past day (not today) - show as missed if:
      // 1. Explicitly marked as missed in logs (completed=false), OR
      // 2. Not completed (should be marked as missed by auto-mark)
      if (isMissed || !isCompleted) {
        classes.push('day-missed');
      }
    }
    // Future days get no special class

    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const dayDate = new Date(year, month, day);
    if (dayDate.getDay() === 0) {
      classes.push('week-divider');
    }

    return classes.join(' ');
  }

  getDaysArray(): number[] {
    const days: number[] = [];
    const startDay = this.getStartDay();
    const daysInMonth = this.getDaysInMonth();
    for (let day = startDay; day <= daysInMonth; day++) {
      days.push(day);
    }
    return days;
  }

  getDayTitle(habitId: string, day: number): string {
    const dateStr = this.getDateString(day);
    if (this.isDayCompleted(habitId, day)) {
      return `${dateStr}: Completed`;
    } else if (this.isDayMissed(habitId, day)) {
      return `${dateStr}: Marked as missed (locked)`;
    } else if (this.isToday(day)) {
      return `Today - mark when completed`;
    } else if (this.isPastDay(day)) {
      return `${dateStr}: Past day`;
    } else {
      return `${dateStr}: Future day`;
    }
  }
}
