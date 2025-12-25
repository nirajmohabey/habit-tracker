import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

const API_URL = environment.apiUrl;

export interface Habit {
  id: string;
  name: string;
  emoji: string;
  category: string;
  goal: number;
  created_at?: string;
}

export interface HabitLog {
  id: string;
  habit_id: string;
  date: string;
  completed: boolean;
}

export interface DailyLogs {
  [date: string]: { [habitId: string]: boolean };
}

export interface Stats {
  habits: Array<{
    habit_id: string;
    name: string;
    emoji: string;
    category: string;
    completed: number;
    goal: number;
    remaining: number;
    percentage: number;
    streak: number;
  }>;
  categories: Array<{
    category: string;
    completed: number;
    goal: number;
    percentage: number;
  }>;
}

export interface WeeklyScorecard {
  week: string;
  completed: number;
  total: number;
  percentage: number;
}

export interface Streak {
  habit_id: string;
  habit_name: string;
  current_streak: number;
  longest_streak: number;
}

export interface Badge {
  name: string;
  description: string;
}

export interface BadgesResponse {
  badges: Badge[];
  total_completed: number;
  total_goal: number;
  percentage: number;
}

export interface Insight {
  type: string;
  message: string;
  icon: string;
}

export interface InsightsResponse {
  insights: Insight[];
  message?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly httpOptions = { withCredentials: true };

  constructor(private http: HttpClient) {}

  // Health check
  healthCheck(): Observable<any> {
    return this.http.get(`${API_URL}/health`, this.httpOptions);
  }

  // Authentication
  checkAuth(): Observable<any> {
    return this.http.get(`${API_URL}/check-auth`, this.httpOptions);
  }

  // Habits
  getHabits(): Observable<Habit[]> {
    return this.http.get<Habit[]>(`${API_URL}/habits`, this.httpOptions);
  }

  createHabit(habit: Partial<Habit>): Observable<Habit> {
    return this.http.post<Habit>(`${API_URL}/habits`, habit, this.httpOptions);
  }

  updateHabit(habitId: string, habit: Partial<Habit>): Observable<Habit> {
    return this.http.put<Habit>(`${API_URL}/habits/${habitId}`, habit, this.httpOptions);
  }

  deleteHabit(habitId: string): Observable<any> {
    return this.http.delete(`${API_URL}/habits/${habitId}`, this.httpOptions);
  }

  // Logs
  getLogs(habitId?: string, startDate?: string, endDate?: string): Observable<HabitLog[]> {
    let params = new HttpParams();
    if (habitId) params = params.set('habit_id', habitId);
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    return this.http.get<HabitLog[]>(`${API_URL}/logs`, { ...this.httpOptions, params });
  }

  toggleLog(habitId: string, date: string, completed: boolean): Observable<any> {
    return this.http.post(`${API_URL}/logs`, {
      habit_id: habitId,
      date: date,
      completed: completed
    }, this.httpOptions);
  }

  getDailyLogs(startDate: string, endDate: string): Observable<DailyLogs> {
    const params = new HttpParams()
      .set('start_date', startDate)
      .set('end_date', endDate);
    return this.http.get<DailyLogs>(`${API_URL}/daily-logs`, { ...this.httpOptions, params });
  }

  // Stats
  getStats(): Observable<Stats> {
    return this.http.get<Stats>(`${API_URL}/stats`, this.httpOptions);
  }

  // Auto-mark missed days
  autoMarkMissedDays(year?: number, month?: number): Observable<any> {
    const body: any = {};
    if (year) body.year = year;
    if (month) body.month = month;
    return this.http.post(`${API_URL}/auto-mark-missed`, body, this.httpOptions);
  }

  // Weekly scorecard
  getWeeklyScorecard(): Observable<WeeklyScorecard[]> {
    return this.http.get<WeeklyScorecard[]>(`${API_URL}/weekly-scorecard`, this.httpOptions);
  }

  // Streaks
  getStreaks(): Observable<Streak[]> {
    return this.http.get<Streak[]>(`${API_URL}/streaks`, this.httpOptions);
  }

  // Badges
  getBadges(): Observable<BadgesResponse> {
    return this.http.get<BadgesResponse>(`${API_URL}/badges`, this.httpOptions);
  }

  // Insights
  getInsights(): Observable<InsightsResponse> {
    return this.http.get<InsightsResponse>(`${API_URL}/insights`, this.httpOptions);
  }
}
