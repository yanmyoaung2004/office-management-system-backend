# School Office Management System - Django Backend

Django REST API backend implementing the School Office Management System as per API_DOCUMENTATION.md.

## Setup

1. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations**
   ```bash
   python manage.py migrate
   ```

4. **Seed initial data (optional)**
   ```bash
   python manage.py seed_data
   ```
   Creates:
   - Admin: `admin` / `admin123`
   - Staff: `staff` / `staff123`
   - Sample majors, intake, student, enquiry

5. **Run server**
   ```bash
   python manage.py runserver
   ```
   API base: `http://localhost:8000/api`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login (username, password) |
| POST | `/api/auth/logout` | Logout (Bearer token) |
| GET/POST | `/api/users` | List/Create users |
| GET/PUT/DELETE | `/api/users/:id` | User CRUD |
| GET/POST | `/api/majors` | List/Create majors |
| GET/PUT/DELETE | `/api/majors/:id` | Major CRUD |
| GET/POST | `/api/intakes` | List/Create intakes |
| GET/PUT/DELETE | `/api/intakes/:id` | Intake CRUD |
| GET/POST | `/api/students` | List/Create students |
| GET/PUT/DELETE | `/api/students/:id` | Student CRUD |
| POST | `/api/students/:id/promote` | Promote student |
| GET/POST | `/api/enquiries` | List/Create enquiries |
| GET/PUT/DELETE | `/api/enquiries/:id` | Enquiry CRUD |
| GET/POST | `/api/enquiries/:id/followups` | List/Create follow-ups |
| GET/PUT/DELETE | `/api/followups/:id` | Follow-up CRUD |
| GET/POST | `/api/reports` | List/Create reports |
| GET | `/api/reports/stats` | Report statistics |
| GET/PUT/DELETE | `/api/reports/:id` | Report CRUD |
| GET/POST | `/api/dropouts` | List/Create dropouts |
| DELETE | `/api/dropouts/:id` | Delete dropout |

## Authentication

- **Login** returns a JWT `token` in the response. Use it as:
  ```
  Authorization: Bearer <token>
  ```
- All endpoints except `/auth/login` require authentication.

## Response Format

- Success: `{ "success": true, "data": {...}, "message": "..." }`
- Error: `{ "success": false, "error": "...", "code": "ERROR_CODE" }`
- List with pagination: `{ "success": true, "data": [...], "pagination": { "page", "limit", "total", "totalPages" } }`
