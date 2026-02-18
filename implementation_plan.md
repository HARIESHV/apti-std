# Implementation Plan - Meet Link Management [COMPLETED]

## Goal
Implement a robust management system for Google Meet links in the aptitude platform. This will allow admins to maintain a library of common links and easily toggle their visibility on student dashboards.

## 1. Database Model Update [x]
- **Add `MeetLink` Model** in `app.py`:
  - `id`: Primary Key
  - `label`: Name of the meeting (e.g., "Daily Standup", "Doubt Clearing Session")
  - `url`: The Google Meet URL
  - `is_active`: Boolean to control visibility to students
  - `created_at`: Timestamp for sorting
- **Keep `Classroom` Model**: This will remain for the "Global Live Classroom" status, which is a specific, high-priority link.

## 2. Backend Routes (`app.py`) [x]
- `GET /admin/dashboard`: Updated to fetch and display all meet links.
- `POST /admin/add_meet_link`: Add a new link to the library.
- `POST /admin/toggle_meet_link/<int:link_id>`: Toggle the `is_active` status of a specific link.
- `POST /admin/delete_meet_link/<int:link_id>`: Remove a link from the library.

## 3. UI Updates [x]
### Admin Dashboard (`templates/admin_dashboard.html`)
- Added a new "Meet Link Library" section below "Classroom Management".
- Simple form to add new links (Label and URL).
- List existing links with toggle switches for "Live/Hidden" and a delete button.

### Student Dashboard (`templates/student_dashboard.html`)
- Added "Active Discussion Sessions" section.
- Displays all links from the `MeetLink` model where `is_active=True`.
- Retained global "Live Classroom" banner at the top.

## 4. Verification Steps [x]
- Create multiple meet links with different labels.
- Toggle links and verify they appear/disappear on the student dashboard.
- Ensure URL validation (from `meet_utils.py`) is applied to new links.
- Test deletion and modification (via toggle).
