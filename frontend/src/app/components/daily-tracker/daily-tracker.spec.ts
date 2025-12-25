import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DailyTracker } from './daily-tracker';

describe('DailyTracker', () => {
  let component: DailyTracker;
  let fixture: ComponentFixture<DailyTracker>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DailyTracker]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DailyTracker);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
