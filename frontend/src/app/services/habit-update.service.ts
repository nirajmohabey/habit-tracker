import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class HabitUpdateService {
  private habitToggledSubject = new Subject<void>();
  public habitToggled$ = this.habitToggledSubject.asObservable();

  /**
   * Notify that a habit has been toggled
   */
  notifyHabitToggled() {
    this.habitToggledSubject.next();
  }
}

