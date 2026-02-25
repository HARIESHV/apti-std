-- =============================================================================
--  AptitudePro — Student–Admin Web Portal
--  MariaDB Production Schema
--  Generated : 2026-02-25
--  Encoding  : UTF-8 (utf8mb4)
--
--  Run this file once on a fresh MariaDB instance:
--      mysql -u <user> -p <database> < schema.sql
--
--  Table overview
--  ──────────────
--  Authentication / Users
--    users              — unified table for students AND admins (role-based)
--
--  Academic Configuration
--    subjects           — aptitude subject catalogue
--    classroom          — global classroom / platform settings (singleton)
--    meet_links         — saved Google Meet links
--
--  Questions & Answers
--    questions          — admin-posted questions (MCQ / open-ended)
--    answers            — student submissions for each question
--    attempts           — tracks the moment a student first opens a question
--
--  Student Profile
--    student_details    — extended academic/personal profile per student
--    student_files      — student-uploaded PDF / document files
--
--  Performance Testing
--    performance_tests  — admin-created test sets
--    performance_results— per-student evaluation results for each test
--
--  Messaging
--    messages           — bidirectional messages between admin and students
--
--  Attendance & Activity
--    attendance         — daily attendance record per student
--    login_logs         — every login attempt (success / failed)
--    activity_logs      — general audit trail (register, update, etc.)
--
--  Notifications
--    notifications      — admin inbox alerts (new registration, new submission…)
-- =============================================================================

-- Ensure a clean run (drop in reverse FK order only if you want a full reset).
-- Commented out by default to protect production data.
-- SET FOREIGN_KEY_CHECKS = 0;
-- DROP TABLE IF EXISTS notifications, activity_logs, login_logs, attendance,
--   messages, performance_results, performance_tests, student_files,
--   student_details, attempts, answers, questions, meet_links, classroom,
--   subjects, users;
-- SET FOREIGN_KEY_CHECKS = 1;

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- =============================================================================
-- 1. SUBJECTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS subjects (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100)    NOT NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uq_subject_name (name)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Aptitude subject catalogue (Quantitative, Logical, etc.)';

-- =============================================================================
-- 2. USERS  (students + admins in one table — role-based access)
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id                      INT UNSIGNED    NOT NULL AUTO_INCREMENT,

    -- ── Authentication ───────────────────────────────────────────────────────
    username                VARCHAR(80)     NOT NULL,
    password_hash           VARCHAR(255)    NOT NULL            COMMENT 'Werkzeug/bcrypt hash',
    visible_password        VARCHAR(100)    DEFAULT NULL        COMMENT 'Alphanumeric admin-visible copy (optional)',
    role                    ENUM('student','admin') NOT NULL DEFAULT 'student',
    is_active               TINYINT(1)      NOT NULL DEFAULT 1,

    -- ── Basic Profile ────────────────────────────────────────────────────────
    full_name               VARCHAR(120)    DEFAULT NULL,
    email                   VARCHAR(150)    DEFAULT NULL,
    phone                   VARCHAR(20)     DEFAULT NULL,
    date_of_birth           DATE            DEFAULT NULL,
    gender                  ENUM('male','female','other','prefer_not_to_say') DEFAULT NULL,
    address                 TEXT            DEFAULT NULL,

    -- ── Academic Profile ─────────────────────────────────────────────────────
    institution             VARCHAR(200)    DEFAULT NULL        COMMENT 'College / school name',
    department              VARCHAR(100)    DEFAULT NULL,
    year_of_study           TINYINT UNSIGNED DEFAULT NULL       COMMENT '1–6',
    batch                   VARCHAR(50)     DEFAULT NULL        COMMENT 'E.g. "2024–2026"',
    enrollment_no           VARCHAR(50)     DEFAULT NULL,

    -- ── Profile Photo ────────────────────────────────────────────────────────
    profile_image           VARCHAR(100)    DEFAULT NULL        COMMENT 'Original filename (legacy/filesystem)',
    profile_image_data      LONGBLOB        DEFAULT NULL        COMMENT 'Binary image stored in DB',
    profile_image_mimetype  VARCHAR(50)     DEFAULT NULL,

    -- ── Timestamps ───────────────────────────────────────────────────────────
    created_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_username      (username),
    UNIQUE KEY uq_email         (email),
    KEY        idx_role         (role),
    KEY        idx_is_active    (is_active)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Unified user table – role column distinguishes student vs. admin';

-- =============================================================================
-- 3. CLASSROOM  (platform-wide settings singleton — always 1 row)
-- =============================================================================
CREATE TABLE IF NOT EXISTS classroom (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    active_meet_link    VARCHAR(500)    NOT NULL DEFAULT 'https://meet.google.com/',
    detected_title      VARCHAR(200)    NOT NULL DEFAULT 'Official Classroom',
    is_live             TINYINT(1)      NOT NULL DEFAULT 0,
    registration_open   TINYINT(1)      NOT NULL DEFAULT 1,
    admin_phone         VARCHAR(20)     NOT NULL DEFAULT '',
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Global platform settings (singleton – only one row used)';

-- =============================================================================
-- 4. MEET_LINKS  (saved Google Meet links for classes)
-- =============================================================================
CREATE TABLE IF NOT EXISTS meet_links (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    label       VARCHAR(100)    DEFAULT NULL,
    url         VARCHAR(500)    NOT NULL,
    is_active   TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_is_active (is_active)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Admin-saved Google Meet / video conference links';

-- =============================================================================
-- 5. QUESTIONS  (admin-posted aptitude questions)
-- =============================================================================
CREATE TABLE IF NOT EXISTS questions (
    id                      INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    subject_id              INT UNSIGNED    DEFAULT NULL,

    -- ── Content ──────────────────────────────────────────────────────────────
    text                    TEXT            NOT NULL            COMMENT 'Question body (HTML allowed)',
    topic                   VARCHAR(100)    DEFAULT NULL,
    question_type           ENUM('mcq','open','file') NOT NULL DEFAULT 'mcq',

    -- ── MCQ Options ──────────────────────────────────────────────────────────
    option_a                VARCHAR(500)    DEFAULT NULL,
    option_b                VARCHAR(500)    DEFAULT NULL,
    option_c                VARCHAR(500)    DEFAULT NULL,
    option_d                VARCHAR(500)    DEFAULT NULL,
    correct_answer          CHAR(1)         DEFAULT NULL        COMMENT 'A / B / C / D',
    explanation             TEXT            DEFAULT NULL,

    -- ── Media ────────────────────────────────────────────────────────────────
    image_file              VARCHAR(100)    DEFAULT NULL,
    image_data              LONGBLOB        DEFAULT NULL,
    image_mimetype          VARCHAR(50)     DEFAULT NULL,
    meet_link               VARCHAR(500)    DEFAULT NULL,

    -- ── Timer ────────────────────────────────────────────────────────────────
    time_limit              INT UNSIGNED    NOT NULL DEFAULT 10  COMMENT 'Fallback / minutes',
    timer_days              INT UNSIGNED    NOT NULL DEFAULT 0,
    timer_hours             INT UNSIGNED    NOT NULL DEFAULT 0,
    timer_minutes           INT UNSIGNED    NOT NULL DEFAULT 0,
    timer_seconds           INT UNSIGNED    NOT NULL DEFAULT 0,
    timer_display_format    ENUM('days','hours') NOT NULL DEFAULT 'days',

    -- ── Lifecycle ────────────────────────────────────────────────────────────
    status                  ENUM('active','closed','draft') NOT NULL DEFAULT 'active',
    scheduled_date          DATE            DEFAULT NULL        COMMENT 'NULL = visible immediately',
    created_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_subject_id      (subject_id),
    KEY idx_status          (status),
    KEY idx_scheduled_date  (scheduled_date),
    KEY idx_created_at      (created_at),

    CONSTRAINT fk_questions_subject
        FOREIGN KEY (subject_id)
        REFERENCES subjects (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Questions posted by admin (MCQ, open-ended, or file-upload)';

-- =============================================================================
-- 6. ANSWERS  (student submissions for each question)
-- =============================================================================
CREATE TABLE IF NOT EXISTS answers (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    student_id          INT UNSIGNED    NOT NULL,
    question_id         INT UNSIGNED    NOT NULL,

    -- ── Response ─────────────────────────────────────────────────────────────
    selected_option     CHAR(1)         DEFAULT NULL            COMMENT 'A / B / C / D (MCQ)',
    text_response       TEXT            DEFAULT NULL            COMMENT 'Open-ended text answer',
    file_path           VARCHAR(200)    DEFAULT NULL,
    file_data           LONGBLOB        DEFAULT NULL,
    file_mimetype       VARCHAR(50)     DEFAULT NULL,
    file_name           VARCHAR(100)    DEFAULT NULL,

    -- ── Evaluation ───────────────────────────────────────────────────────────
    is_correct          TINYINT(1)      DEFAULT NULL            COMMENT 'NULL = pending evaluation',
    score               DECIMAL(5,2)    NOT NULL DEFAULT 0.00,
    admin_feedback      TEXT            DEFAULT NULL            COMMENT 'Admin evaluation remarks',

    -- ── Meta ─────────────────────────────────────────────────────────────────
    time_taken_sec      INT UNSIGNED    NOT NULL DEFAULT 0,
    is_suspicious       TINYINT(1)      NOT NULL DEFAULT 0      COMMENT 'Flagged for abnormally fast submission',
    attempt_number      TINYINT UNSIGNED NOT NULL DEFAULT 1,
    is_expired          TINYINT(1)      NOT NULL DEFAULT 0,
    submitted_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_student_id      (student_id),
    KEY idx_question_id     (question_id),
    KEY idx_submitted_at    (submitted_at),
    KEY idx_is_correct      (is_correct),

    CONSTRAINT fk_answers_student
        FOREIGN KEY (student_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_answers_question
        FOREIGN KEY (question_id)
        REFERENCES questions (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='All student answer submissions; is_correct NULL = awaiting admin evaluation';

-- =============================================================================
-- 7. ATTEMPTS  (records the instant a student opens a question — anti-cheat)
-- =============================================================================
CREATE TABLE IF NOT EXISTS attempts (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    student_id  INT UNSIGNED    NOT NULL,
    question_id INT UNSIGNED    NOT NULL,
    start_time  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_student_question (student_id, question_id),
    KEY idx_question_id (question_id),

    CONSTRAINT fk_attempts_student
        FOREIGN KEY (student_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_attempts_question
        FOREIGN KEY (question_id)
        REFERENCES questions (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Records when a student first opens a question (used for timer)';

-- =============================================================================
-- 8. STUDENT_DETAILS  (extended academic / personal profile)
-- =============================================================================
CREATE TABLE IF NOT EXISTS student_details (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED    NOT NULL,

    -- ── Academic ─────────────────────────────────────────────────────────────
    roll_number     VARCHAR(50)     DEFAULT NULL,
    cgpa            DECIMAL(4,2)    DEFAULT NULL,
    skills          TEXT            DEFAULT NULL                COMMENT 'Comma-separated or JSON list',
    achievements    TEXT            DEFAULT NULL,
    about_me        TEXT            DEFAULT NULL,

    -- ── Social / Links ───────────────────────────────────────────────────────
    linkedin_url    VARCHAR(300)    DEFAULT NULL,
    github_url      VARCHAR(300)    DEFAULT NULL,

    -- ── Timestamps ───────────────────────────────────────────────────────────
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_user_id (user_id),

    CONSTRAINT fk_student_details_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Extended student profile data (academic, social, about)';

-- =============================================================================
-- 9. STUDENT_FILES  (student-uploaded PDFs / documents)
-- =============================================================================
CREATE TABLE IF NOT EXISTS student_files (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    student_id      INT UNSIGNED    NOT NULL,

    file_name       VARCHAR(255)    NOT NULL,
    original_name   VARCHAR(255)    DEFAULT NULL,
    file_data       LONGBLOB        DEFAULT NULL                COMMENT 'Binary content stored in DB',
    file_mimetype   VARCHAR(100)    DEFAULT NULL,
    file_size_bytes INT UNSIGNED    DEFAULT NULL,
    description     VARCHAR(300)    DEFAULT NULL,
    category        ENUM('resume','notes','assignment','other') NOT NULL DEFAULT 'other',
    is_visible      TINYINT(1)      NOT NULL DEFAULT 1          COMMENT 'Admin can toggle visibility',
    uploaded_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_student_id  (student_id),
    KEY idx_category    (category),

    CONSTRAINT fk_student_files_student
        FOREIGN KEY (student_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Student-uploaded PDF / document files';

-- =============================================================================
-- 10. PERFORMANCE_TESTS  (admin-created test sets)
-- =============================================================================
CREATE TABLE IF NOT EXISTS performance_tests (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    title           VARCHAR(200)    NOT NULL,
    description     TEXT            DEFAULT NULL,
    subject_id      INT UNSIGNED    DEFAULT NULL,

    total_marks     DECIMAL(6,2)    NOT NULL DEFAULT 100.00,
    passing_marks   DECIMAL(6,2)    NOT NULL DEFAULT 40.00,
    duration_minutes INT UNSIGNED   NOT NULL DEFAULT 60,

    status          ENUM('active','closed','draft') NOT NULL DEFAULT 'draft',
    start_time      DATETIME        DEFAULT NULL,
    end_time        DATETIME        DEFAULT NULL,

    created_by      INT UNSIGNED    NOT NULL                    COMMENT 'Admin user id',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_status      (status),
    KEY idx_subject_id  (subject_id),
    KEY idx_created_by  (created_by),

    CONSTRAINT fk_perf_tests_subject
        FOREIGN KEY (subject_id)
        REFERENCES subjects (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_perf_tests_admin
        FOREIGN KEY (created_by)
        REFERENCES users (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Admin-created performance/mock test metadata';

-- =============================================================================
-- 11. PERFORMANCE_RESULTS  (per-student evaluation for each test)
-- =============================================================================
CREATE TABLE IF NOT EXISTS performance_results (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    test_id         INT UNSIGNED    NOT NULL,
    student_id      INT UNSIGNED    NOT NULL,

    marks_obtained  DECIMAL(6,2)    NOT NULL DEFAULT 0.00,
    percentage      DECIMAL(5,2)    GENERATED ALWAYS AS (
                        (marks_obtained / (SELECT total_marks FROM performance_tests WHERE id = test_id)) * 100
                    ) VIRTUAL,
    rank_in_test    SMALLINT UNSIGNED DEFAULT NULL,
    grade           CHAR(2)         DEFAULT NULL                COMMENT 'A+, A, B+, B, C, D, F',
    passed          TINYINT(1)      DEFAULT NULL,

    admin_remarks   TEXT            DEFAULT NULL,
    evaluated_at    DATETIME        DEFAULT NULL,
    submitted_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_test_student  (test_id, student_id),
    KEY idx_student_id          (student_id),

    CONSTRAINT fk_perf_results_test
        FOREIGN KEY (test_id)
        REFERENCES performance_tests (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_perf_results_student
        FOREIGN KEY (student_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Per-student results and evaluation data for each performance test';

-- =============================================================================
-- 12. MESSAGES  (bidirectional messaging between admin and students)
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    sender_id       INT UNSIGNED    NOT NULL,
    receiver_id     INT UNSIGNED    DEFAULT NULL                COMMENT 'NULL = broadcast to all students',

    -- ── Content ──────────────────────────────────────────────────────────────
    content         TEXT            DEFAULT NULL,
    file_data       LONGBLOB        DEFAULT NULL,
    file_mimetype   VARCHAR(100)    DEFAULT NULL,
    file_name       VARCHAR(255)    DEFAULT NULL,

    -- ── State ────────────────────────────────────────────────────────────────
    is_read         TINYINT(1)      NOT NULL DEFAULT 0,
    is_broadcast    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_sender_id   (sender_id),
    KEY idx_receiver_id (receiver_id),
    KEY idx_created_at  (created_at),
    KEY idx_is_read     (is_read),

    CONSTRAINT fk_messages_sender
        FOREIGN KEY (sender_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_messages_receiver
        FOREIGN KEY (receiver_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Bidirectional messages between admin and students; receiver_id NULL = broadcast';

-- =============================================================================
-- 13. ATTENDANCE  (daily record per student)
-- =============================================================================
CREATE TABLE IF NOT EXISTS attendance (
    id                      INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id                 INT UNSIGNED    NOT NULL,
    date                    DATE            NOT NULL,

    first_login             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    total_minutes_online    INT UNSIGNED    NOT NULL DEFAULT 0,

    PRIMARY KEY (id),
    UNIQUE KEY uq_user_date     (user_id, date),
    KEY        idx_date         (date),

    CONSTRAINT fk_attendance_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Daily attendance record; one row per student per calendar day';

-- =============================================================================
-- 14. LOGIN_LOGS  (every login attempt with IP + device info)
-- =============================================================================
CREATE TABLE IF NOT EXISTS login_logs (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id             INT UNSIGNED    NOT NULL,

    login_time          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address          VARCHAR(45)     DEFAULT NULL            COMMENT 'IPv4 or IPv6',
    user_agent          VARCHAR(512)    DEFAULT NULL,
    device_fingerprint  VARCHAR(255)    DEFAULT NULL,
    status              ENUM('success','failed') NOT NULL DEFAULT 'success',

    PRIMARY KEY (id),
    KEY idx_user_id     (user_id),
    KEY idx_login_time  (login_time),
    KEY idx_status      (status),

    CONSTRAINT fk_login_logs_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Every login attempt; used for security auditing and multi-IP detection';

-- =============================================================================
-- 15. ACTIVITY_LOGS  (general audit trail)
-- =============================================================================
CREATE TABLE IF NOT EXISTS activity_logs (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id     INT UNSIGNED    DEFAULT NULL,

    action      VARCHAR(100)    NOT NULL                        COMMENT 'e.g. LOGIN, REGISTER, SUBMIT, PROFILE_UPDATE',
    details     TEXT            DEFAULT NULL,
    event_time  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_user_id     (user_id),
    KEY idx_action      (action),
    KEY idx_event_time  (event_time),

    CONSTRAINT fk_activity_logs_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Audit trail – records every significant system event';

-- =============================================================================
-- 16. NOTIFICATIONS  (admin inbox alerts)
-- =============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    type            VARCHAR(50)     DEFAULT NULL                COMMENT 'register, login, submit, message, etc.',

    -- ── Source ───────────────────────────────────────────────────────────────
    student_id      INT UNSIGNED    DEFAULT NULL,
    student_name    VARCHAR(120)    DEFAULT NULL,
    question_id     INT UNSIGNED    DEFAULT NULL,
    question_text   VARCHAR(300)    DEFAULT NULL,

    -- ── Payload ──────────────────────────────────────────────────────────────
    is_correct      TINYINT(1)      DEFAULT NULL,
    is_read         TINYINT(1)      NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_type        (type),
    KEY idx_is_read     (is_read),
    KEY idx_student_id  (student_id),
    KEY idx_created_at  (created_at),

    CONSTRAINT fk_notifications_student
        FOREIGN KEY (student_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_notifications_question
        FOREIGN KEY (question_id)
        REFERENCES questions (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Admin inbox – alerts for registrations, logins, submissions, messages';

-- =============================================================================
-- SEED DATA
-- =============================================================================

-- 1. Default subjects
INSERT IGNORE INTO subjects (name) VALUES
    ('Quantitative Aptitude'),
    ('Logical Reasoning'),
    ('Verbal Ability'),
    ('Data Interpretation');

-- 2. Default classroom singleton row
INSERT IGNORE INTO classroom (id, active_meet_link, detected_title, is_live, registration_open, admin_phone)
VALUES (1, 'https://meet.google.com/', 'Official Classroom', 0, 1, '');

-- 3. Default admin account
--    ⚠️  Password stored here is plain-text 'admin123' for seeding only.
--    In production the Flask app hashes it with Werkzeug; replace the hash
--    below with your own Werkzeug-generated hash, or let init_db() do it.
--    To generate a Werkzeug hash in Python:
--        from werkzeug.security import generate_password_hash
--        print(generate_password_hash('your_password'))
INSERT IGNORE INTO users
    (username, password_hash, role, full_name, is_active)
VALUES
    ('admin',
     'pbkdf2:sha256:600000$change_this_placeholder$0000000000000000000000000000000000000000000000000000000000000000',
     'admin',
     'Administrator',
     1);

-- =============================================================================
-- RELATIONSHIP SUMMARY
-- =============================================================================
--
--  users ──────────────────────────────────────────── (PK: users.id)
--      │
--      ├──< answers            (student_id  → users.id CASCADE DELETE)
--      ├──< attempts           (student_id  → users.id CASCADE DELETE)
--      ├──< student_details    (user_id     → users.id CASCADE DELETE, 1-to-1)
--      ├──< student_files      (student_id  → users.id CASCADE DELETE)
--      ├──< attendance         (user_id     → users.id CASCADE DELETE)
--      ├──< login_logs         (user_id     → users.id CASCADE DELETE)
--      ├──< activity_logs      (user_id     → users.id SET NULL on delete)
--      ├──< notifications      (student_id  → users.id CASCADE DELETE)
--      ├──< messages (sender)  (sender_id   → users.id CASCADE DELETE)
--      ├──< messages (recv)    (receiver_id → users.id CASCADE DELETE)
--      └──< performance_results(student_id  → users.id CASCADE DELETE)
--
--  subjects ─────────────────────────────────────────── (PK: subjects.id)
--      │
--      ├──< questions          (subject_id  → subjects.id SET NULL on delete)
--      └──< performance_tests  (subject_id  → subjects.id SET NULL on delete)
--
--  questions ────────────────────────────────────────── (PK: questions.id)
--      │
--      ├──< answers            (question_id → questions.id CASCADE DELETE)
--      ├──< attempts           (question_id → questions.id CASCADE DELETE)
--      └──< notifications      (question_id → questions.id SET NULL on delete)
--
--  performance_tests ────────────────────────────────── (PK: performance_tests.id)
--      │
--      └──< performance_results(test_id    → performance_tests.id CASCADE DELETE)
--
-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
