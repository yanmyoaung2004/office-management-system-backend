# Teacher Scheduling Module — API Reference

Base URLs:
- Exam module: `/api/exam/`
- Admission module: `/api/admission/`

All endpoints require JWT auth header:
```
Authorization: Bearer <access_token>
```

All responses follow the standard format:
```json
{ "success": true/false, "data": ..., "message": "..." }
```

---

## 1. Teacher CRUD

### 1.1 List All Teachers

```
GET /api/exam/teachers/
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "TE-ABC123",
      "name": "John Doe",
      "phone_number": "+260991234567",
      "email": "john@sti.edu",
      "subject_ids": [],
      "subjects_display": [
        { "id": "SU-xxx", "code": "CF", "name": "Computer Fundamental" }
      ],
      "created_at": "2026-05-23T10:00:00Z",
      "updated_at": "2026-05-23T10:00:00Z"
    }
  ]
}
```

### 1.2 Create Teacher

```
POST /api/exam/teachers/
```

**Payload:**
```json
{
  "name": "John Doe",
  "phone_number": "+260991234567",
  "email": "john@sti.edu",
  "subject_ids": ["SU-XXXXX", "SU-YYYYY"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Teacher's full name |
| `phone_number` | string | yes | Contact number |
| `email` | string | no | Email address |
| `subject_ids` | string[] | no | Array of Subject PKs this teacher can teach |

**Response** (201):
```json
{
  "success": true,
  "data": {
    "id": "TE-ABC123",
    "name": "John Doe",
    "phone_number": "+260991234567",
    "email": "john@sti.edu",
    "subject_ids": ["SU-XXXXX"],
    "subjects_display": [
      { "id": "SU-XXXXX", "code": "CF", "name": "Computer Fundamental" }
    ]
  },
  "message": "Teacher created."
}
```

**Auto-seeded availability:** All 15 weekly slots (5 days × 3 slots) are automatically created with `is_available: true` for every new teacher.

### 1.3 Get Single Teacher

```
GET /api/exam/teachers/<teacher_id>
```

### 1.4 Update Teacher

```
PUT /api/exam/teachers/<teacher_id>
```

**Payload** (same as create):
```json
{
  "name": "John Updated",
  "phone_number": "+260991234567",
  "email": "john@sti.edu",
  "subject_ids": ["SU-XXXXX", "SU-ZZZZZ"]
}
```

**Note:** This **replaces** the subject list entirely. Send all subjects the teacher should teach.

### 1.5 Delete Teacher

```
DELETE /api/exam/teachers/<teacher_id>
```

**Response:**
```json
{ "success": true, "message": "Teacher deleted." }
```

---

## 2. Teacher Availability

Each teacher has 15 weekly time slots. `is_available` is the single source of truth:
- `true` = slot is free
- `false` = slot is booked by a timetable (any intake)

Toggled automatically when timetable is generated, cleared, or manually updated.

### 2.1 Get Availability

```
GET /api/exam/teachers/<teacher_id>/availability/
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "teacher": "TE-ABC123",
      "day_of_week": 1,
      "slot": "9-11",
      "is_available": false,
      "intake": "CS1",
      "subject": "CF"
    },
    {
      "id": 2,
      "teacher": "TE-ABC123",
      "day_of_week": 1,
      "slot": "12-2",
      "is_available": true,
      "intake": null,
      "subject": null
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `is_available` | `true` = free, `false` = booked by a timetable |
| `intake` | Intake code of the assigned class (null if free) |
| `subject` | Subject **code** of the assigned class (null if free), e.g. `"CF"` |

**Slot values:** `9-11`, `12-2`, `2-4`
**Day values:** 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri

### 2.2 Set Availability (Batch)

```
POST /api/exam/teachers/<teacher_id>/availability/
```

Replaces all 15 slots. Send all 15 rows.

**Payload:**
```json
{
  "availabilities": [
    { "teacher": "TE-ABC123", "day_of_week": 1, "slot": "9-11", "is_available": true },
    { "teacher": "TE-ABC123", "day_of_week": 1, "slot": "12-2", "is_available": true },
    { "teacher": "TE-ABC123", "day_of_week": 1, "slot": "2-4", "is_available": false },
    ... (all 15 slots)
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `teacher` | string | no | Can omit — the URL already identifies the teacher |
| `day_of_week` | int | yes | 1-5 |
| `slot` | string | yes | `9-11`, `12-2`, or `2-4` |
| `is_available` | bool | no | Defaults to `true` |

---

## 3. Subject Frequencies

Set how many classes per week each subject gets for a specific intake+semester.

### 3.1 Get Frequencies

```
GET /api/exam/intakes/<intake_id>/semesters/<semester_id>/subject-frequencies/
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "ISF-xxx",
      "intake": "INT-xxx",
      "semester": "SEM-xxx",
      "subject": "SU-XXXXX",
      "subject_code": "CF",
      "subject_name": "Computer Fundamental",
      "frequency": 3
    }
  ]
}
```

### 3.2 Set Frequency (Single or Bulk)

```
POST /api/exam/intakes/<intake_id>/semesters/<semester_id>/subject-frequencies/
```

Accepts a **single object** or an **array of objects**.

**Single:**
```json
{ "subject": "SU-XXXXX", "frequency": 3 }
```

**Bulk:**
```json
[
  { "subject": "SU-XXXXX", "frequency": 3 },
  { "subject": "SU-YYYYY", "frequency": 2 }
]
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | string | yes | Subject PK |
| `frequency` | integer | yes | Classes per week (1-15) |

**Note:** Sum of all frequencies **must not exceed 15**.

### 3.3 Delete Frequency(s)

```
DELETE /api/exam/intakes/<intake_id>/semesters/<semester_id>/subject-frequencies/?subject=SU-XXXXX
```

| Query Param | Description |
|-------------|-------------|
| `subject` | (optional) Delete only this subject's frequency. Omit to delete ALL. |

---

## 4. Timetable Generation

### 4.1 Generate Timetable

```
POST /api/exam/intakes/<intake_id>/semesters/<semester_id>/timetable/generate/
```

No request body.

**Algorithm:**
1. Validates total frequencies ≤ 15
2. Restores `is_available` for this intake's old slots
3. Collects teachers grouped by subject, and their available slots
4. Checks existing timetables from **other intakes** to prevent double-booking
5. Assigns subjects highest-frequency-first, distributing across the week evenly (Mon 9-11 → Tue 9-11 → Wed 9-11 → ...)
6. If any subject can't get enough available slots → **error 400, nothing saved**

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "intake": "INT-xxx",
    "semester": "SEM-xxx",
    "timetable": [
      {
        "day": 1, "day_label": "Monday",
        "slots": [
          { "slot": "9-11", "subject_code": "CF", "subject_name": "Computer Fundamental", "teacher_name": "John Doe" },
          { "slot": "12-2", "subject_code": "P01", "subject_name": "Programming C", "teacher_name": "Jane Smith" },
          { "slot": "2-4", "subject_code": null, "subject_name": null, "teacher_name": null }
        ]
      },
      { "day": 2, "day_label": "Tuesday", "slots": [...] },
      { "day": 3, "day_label": "Wednesday", "slots": [...] },
      { "day": 4, "day_label": "Thursday", "slots": [...] },
      { "day": 5, "day_label": "Friday", "slots": [...] }
    ]
  },
  "message": "Timetable generated."
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": [
    "Subject 'CS-01' needs 3 slots but only 2 are available. Add more teachers or reduce frequency."
  ],
  "code": "TIMETABLE_ERRORS"
}
```

**Availability side-effect:** On success, each assigned slot has `is_available` set to `false` for that teacher.

### 4.2 View Timetable

```
GET /api/exam/intakes/<intake_id>/semesters/<semester_id>/timetable/
```

Response same structure as generate success (without the message field).

### 4.3 Update Single Slot (Manual Fix)

```
PUT /api/exam/intakes/<intake_id>/semesters/<semester_id>/timetable/
```

**Payload:**
```json
{
  "day_of_week": 1,
  "slot": "2-4",
  "subject": "SU-XXXXX",
  "teacher": "TE-ABC123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `day_of_week` | int | yes | 1-5 |
| `slot` | string | yes | `9-11`, `12-2`, or `2-4` |
| `subject` | string | yes | Subject PK |
| `teacher` | string | yes | Teacher PK |

**Availability side-effect:** Old slot's `is_available` restored to `true`, new slot's set to `false`.

### 4.4 Clear Timetable

```
DELETE /api/exam/intakes/<intake_id>/semesters/<semester_id>/timetable/
```

**Availability side-effect:** All cleared slots have `is_available` restored to `true`.

---

## 5. Workflow Summary

### Setup (once)
1. **Create teachers** → `POST /api/exam/teachers/` with `subject_ids`
   - 15 availability slots auto-created (all available)
2. **Restrict availability (optional)** → `POST /api/exam/teachers/<id>/availability/`

### Per Intake+Semester
3. **Set frequencies** → `POST /api/exam/intakes/<id>/semesters/<id>/subject-frequencies/`
4. **Generate timetable** → `POST /api/exam/intakes/<id>/semesters/<id>/timetable/generate/`
   - On error → adjust frequencies or add teachers, retry
5. **Manual fix** → `PUT /api/exam/intakes/<id>/semesters/<id>/timetable/`
6. **View timetable** → `GET /api/exam/intakes/<id>/semesters/<id>/timetable/`
7. **View teacher availability** → `GET /api/exam/teachers/<id>/availability/`

---

## 6. Subject Hierarchy (Curriculum Tree)

Returns all subjects organized by Major → Year → Semester.

```
GET /api/admission/subject-hierarchy
```

No request body.

**Response:**
```json
{
  "success": true,
  "data": {
    "Computer Science": {
      "Foundation": {
        "Semester 1": [
          { "id": "SU-XXXXX", "code": "CF", "name": "Computer Fundamental" },
          { "id": "SU-YYYYY", "code": "P01", "name": "Programming C" }
        ],
        "Semester 2": [
          { "id": "SU-ZZZZZ", "code": "NE1", "name": "Networking 1" }
        ]
      },
      "Year 1": {
        "Semester 1": [
          { "id": "SU-AAAAA", "code": "DS", "name": "Data Structures" }
        ]
      }
    }
  }
}
```

| Level | Key | Value |
|-------|-----|-------|
| Top | Major name | Object of Year → Semester → Subjects |
| 2nd | Year name | Object of Semester → Subjects |
| 3rd | Semester name | Array of `{id, code, name}` |
