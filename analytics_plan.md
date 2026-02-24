# Implementation Plan - Student Management & Analytics

## Goal
Integrate advanced student tracking, attendance automation, performance analytics, and security monitoring into the Aptipro platform.

## 1. Database Schema Updates
### New Models:
- **`Subject`**: Categorize questions and track performance by area.
- **`LoginLog`**: Track IP, User-Agent, and device fingerprint for security audits.
- **`Attendance`**: Daily summary of student activity (first login, last active, duration).

### Model Extensions:
- **`User`**: Add `is_active` status.
- **`Question`**: Add `subject_id` for better categorization.
- **`Answer`**: Add `score`, `time_taken_sec`, `is_suspicious`, and `attempt_number`.

## 2. Backend Logic Integration
### Authentication & Attendance:
- **Login**: Record entry in `LoginLog`. Check/Create daily `Attendance` record.
- **Heartbeat**: New route `/api/heartbeat` to update student's `last_active` timestamp.

### Answer Analysis:
- **Submission**: Calculate duration based on `Attempt` start time.
- **Cheating Detection**: Flag submissions with extremely low durations (e.g., < 3s for complex topics).

## 3. UI & Reporting
- **Admin Stats**: New "Attendance Report" and "Suspicious Activity" tabs.
- **Student Profile**: Show performance trends by Subject.

## 4. Execution Steps
1. Add new models and update `init_db` migration logic. [ ]
2. Implement `LoginLog` and `Attendance` updates in `/login`. [ ]
3. Implement heartbeat mechanism. [ ]
4. Update submission logic for performance tracking. [ ]
5. Create Admin Reports UI. [ ]
