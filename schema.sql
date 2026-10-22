-- ============================================================================
-- Smart Student Management System (SSMS) - MySQL Database Schema
-- Compatible with MySQL 8.0+ / MariaDB 10.5+
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `ssms_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `ssms_db`;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Users Table (Authentication & RBAC)
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('admin', 'teacher', 'student', 'accountant') NOT NULL DEFAULT 'student',
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `full_name` VARCHAR(100) NOT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Courses Table
DROP TABLE IF EXISTS `courses`;
CREATE TABLE `courses` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `code` VARCHAR(20) NOT NULL UNIQUE,
    `name` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `duration_semesters` INT DEFAULT 8
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Subjects Table
DROP TABLE IF EXISTS `subjects`;
CREATE TABLE `subjects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `code` VARCHAR(20) NOT NULL UNIQUE,
    `name` VARCHAR(100) NOT NULL,
    `course_id` INT NOT NULL,
    `semester` INT NOT NULL,
    `credits` INT DEFAULT 4,
    `max_internal` INT DEFAULT 30,
    `max_external` INT DEFAULT 70,
    `pass_marks` INT DEFAULT 40,
    CONSTRAINT `fk_subjects_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Students Table
DROP TABLE IF EXISTS `students`;
CREATE TABLE `students` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` VARCHAR(30) NOT NULL UNIQUE,
    `user_id` INT NULL,
    `course_id` INT NOT NULL,
    `semester` INT NOT NULL DEFAULT 1,
    `first_name` VARCHAR(50) NOT NULL,
    `last_name` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `phone` VARCHAR(20) NOT NULL,
    `address` TEXT,
    `enrollment_date` DATE NOT NULL,
    `status` ENUM('active', 'inactive', 'graduated', 'dropped') DEFAULT 'active',
    `guardian_name` VARCHAR(100),
    `guardian_phone` VARCHAR(20),
    CONSTRAINT `fk_students_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_students_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE RESTRICT,
    INDEX `idx_students_status` (`status`),
    INDEX `idx_students_sem` (`course_id`, `semester`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Attendance Table
DROP TABLE IF EXISTS `attendance`;
CREATE TABLE `attendance` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `date` DATE NOT NULL,
    `status` ENUM('present', 'absent', 'leave') NOT NULL,
    `remarks` VARCHAR(255),
    `marked_by` INT NULL,
    CONSTRAINT `uq_student_subject_date` UNIQUE (`student_id`, `subject_id`, `date`),
    CONSTRAINT `fk_attendance_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_attendance_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_attendance_marked_by` FOREIGN KEY (`marked_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_attendance_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Exams Table
DROP TABLE IF EXISTS `exams`;
CREATE TABLE `exams` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `exam_type` VARCHAR(50) DEFAULT 'Mid-Term',
    `academic_year` VARCHAR(20) DEFAULT '2026-2027',
    `semester` INT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Marks Table
DROP TABLE IF EXISTS `marks`;
CREATE TABLE `marks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `exam_id` INT NOT NULL,
    `student_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `internal_marks` DECIMAL(5,2) DEFAULT 0.00,
    `external_marks` DECIMAL(5,2) DEFAULT 0.00,
    `total_marks` DECIMAL(5,2) DEFAULT 0.00,
    `percentage` DECIMAL(5,2) DEFAULT 0.00,
    `grade` VARCHAR(5) DEFAULT 'F',
    `status` ENUM('pass', 'fail') DEFAULT 'fail',
    `entered_by` INT NULL,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `uq_exam_student_subject` UNIQUE (`exam_id`, `student_id`, `subject_id`),
    CONSTRAINT `fk_marks_exam` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_marks_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_marks_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_marks_entered_by` FOREIGN KEY (`entered_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Fee Structures Table
DROP TABLE IF EXISTS `fee_structures`;
CREATE TABLE `fee_structures` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `course_id` INT NOT NULL,
    `semester` INT NOT NULL,
    `academic_year` VARCHAR(20) DEFAULT '2026-2027',
    `total_fee` DECIMAL(10,2) NOT NULL DEFAULT 40000.00,
    `due_date` DATE NOT NULL,
    CONSTRAINT `fk_feestructure_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Student Fees Table (Ledger)
DROP TABLE IF EXISTS `student_fees`;
CREATE TABLE `student_fees` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `fee_structure_id` INT NOT NULL,
    `total_amount` DECIMAL(10,2) NOT NULL DEFAULT 40000.00,
    `paid_amount` DECIMAL(10,2) DEFAULT 0.00,
    `balance_amount` DECIMAL(10,2) DEFAULT 40000.00,
    `status` ENUM('paid', 'partial', 'unpaid') DEFAULT 'unpaid',
    CONSTRAINT `fk_studentfees_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_studentfees_structure` FOREIGN KEY (`fee_structure_id`) REFERENCES `fee_structures` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Fee Payments Table (Installments / Receipts)
DROP TABLE IF EXISTS `fee_payments`;
CREATE TABLE `fee_payments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_fee_id` INT NOT NULL,
    `receipt_no` VARCHAR(50) NOT NULL UNIQUE,
    `amount_paid` DECIMAL(10,2) NOT NULL,
    `payment_date` DATE NOT NULL,
    `payment_mode` ENUM('Cash', 'UPI', 'Net Banking', 'Cheque') DEFAULT 'UPI',
    `transaction_ref` VARCHAR(100),
    `collected_by` INT NULL,
    `notes` VARCHAR(255),
    CONSTRAINT `fk_feepayments_studentfee` FOREIGN KEY (`student_fee_id`) REFERENCES `student_fees` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_feepayments_collected_by` FOREIGN KEY (`collected_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_feepayments_date` (`payment_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. Audit Logs Table (Security & Change Tracking)
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `action` VARCHAR(100) NOT NULL,
    `entity_type` VARCHAR(50),
    `entity_id` INT,
    `details` TEXT,
    `ip_address` VARCHAR(50),
    `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_audit_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
