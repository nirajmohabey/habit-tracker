import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AutoMarkService {
  private autoMarkTrigger$ = new Subject<void>();
  
  // Observable that components can subscribe to
  get onAutoMarkRequested() {
    return this.autoMarkTrigger$.asObservable();
  }
  
  // Trigger auto-mark from anywhere
  triggerAutoMark() {
    this.autoMarkTrigger$.next();
  }
}

