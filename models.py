from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User account model supporting Role-Based Access Control."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # admin, teacher, student, accountant
    email = db.Column(db.String(100), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    student_profile = db.relationship('Student', backref='user_account', uselist=False, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Course(db.Model):
    """Academic Course / Department."""
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g., 'BTECH-CE'
    name = db.Column(db.String(100), nullable=False)              # e.g., 'Computer Engineering'
    description = db.Column(db.Text)
    duration_semesters = db.Column(db.Integer, default=8)

    # Relationships
    students = db.relationship('Student', backref='course', lazy='dynamic')
    subjects = db.relationship('Subject', backref='course', lazy='dynamic')
    fee_structures = db.relationship('FeeStructure', backref='course', lazy='dynamic')

    def __repr__(self):
        return f"<Course {self.code}: {self.name}>"


class Subject(db.Model):
    """Academic Subject / Course Unit."""
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g., 'CS401'
    name = db.Column(db.String(100), nullable=False)              # e.g., 'Database Management Systems'
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    credits = db.Column(db.Integer, default=4)
    max_internal = db.Column(db.Integer, default=30)
    max_external = db.Column(db.Integer, default=70)
    pass_marks = db.Column(db.Integer, default=40)

    # Relationships
    attendance_records = db.relationship('Attendance', backref='subject', lazy='dynamic')
    marks_records = db.relationship('Marks', backref='subject', lazy='dynamic')

    @property
    def max_total(self):
        return self.max_internal + self.max_external

    def __repr__(self):
        return f"<Subject {self.code}: {self.name}>"


class Student(db.Model):
    """Student master demographic and enrollment record."""
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(30), unique=True, nullable=False, index=True)  # e.g., 'STU2026001'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False, default=1)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text)
    enrollment_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default='active')  # active, inactive, graduated, dropped
    guardian_name = db.Column(db.String(100))
    guardian_phone = db.Column(db.String(20))

    # Relationships
    attendance_records = db.relationship('Attendance', backref='student', lazy='dynamic')
    marks_records = db.relationship('Marks', backref='student', lazy='dynamic')
    fees = db.relationship('StudentFee', backref='student', lazy='dynamic')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def calculate_attendance_percentage(self, subject_id=None):
        """Calculates attendance percentage either for a specific subject or overall."""
        query = Attendance.query.filter_by(student_id=self.id)
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        total = query.count()
        if total == 0:
            return 100.0  # No sessions logged yet
        present = query.filter(Attendance.status.in_(['present', 'leave'])).count()
        return round((present / total) * 100, 2)

    def is_attendance_defaulter(self, threshold=75.0):
        return self.calculate_attendance_percentage() < threshold

    def __repr__(self):
        return f"<Student {self.student_id}: {self.full_name}>"


class Attendance(db.Model):
    """Daily or lecture-wise attendance entry."""
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(15), nullable=False)  # 'present', 'absent', 'leave'
    remarks = db.Column(db.String(255))
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'date', name='uq_student_subject_date'),
    )

    def __repr__(self):
        return f"<Attendance S:{self.student_id} Sub:{self.subject_id} Date:{self.date} Status:{self.status}>"


class Exam(db.Model):
    """Examination schedule/type."""
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)             # e.g., 'Mid-Term Exam 2026'
    exam_type = db.Column(db.String(50), default='Mid-Term')     # 'Mid-Term', 'Final', 'Quiz'
    academic_year = db.Column(db.String(20), default='2026-2027')
    semester = db.Column(db.Integer, nullable=False, default=1)

    marks = db.relationship('Marks', backref='exam', lazy='dynamic')

    def __repr__(self):
        return f"<Exam {self.name} Sem:{self.semester}>"


class Marks(db.Model):
    """Evaluation marks record per student, subject, and exam."""
    __tablename__ = 'marks'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    internal_marks = db.Column(db.Float, default=0.0)
    external_marks = db.Column(db.Float, default=0.0)
    total_marks = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    grade = db.Column(db.String(5), default='F')
    status = db.Column(db.String(10), default='fail')  # 'pass', 'fail'
    entered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('exam_id', 'student_id', 'subject_id', name='uq_exam_student_subject'),
    )

    def compute_result(self, max_internal=30, max_external=70):
        """Automated calculation of total marks, percentage, grade, and pass/fail status."""
        self.total_marks = round(self.internal_marks + self.external_marks, 2)
        max_total = max_internal + max_external
        if max_total > 0:
            self.percentage = round((self.total_marks / max_total) * 100, 2)
        else:
            self.percentage = 0.0

        # Pass criteria: >= 40% in internal, >= 40% in external, and >= 40% aggregate
        internal_pass = (self.internal_marks / max_internal) >= 0.40 if max_internal > 0 else True
        external_pass = (self.external_marks / max_external) >= 0.40 if max_external > 0 else True

        if internal_pass and external_pass and self.percentage >= 40.0:
            self.status = 'pass'
            if self.percentage >= 85:
                self.grade = 'O'
            elif self.percentage >= 75:
                self.grade = 'A+'
            elif self.percentage >= 65:
                self.grade = 'A'
            elif self.percentage >= 55:
                self.grade = 'B+'
            elif self.percentage >= 45:
                self.grade = 'B'
            else:
                self.grade = 'P'
        else:
            self.status = 'fail'
            self.grade = 'F'

    def __repr__(self):
        return f"<Marks S:{self.student_id} Sub:{self.subject_id} Total:{self.total_marks} Grade:{self.grade}>"


class FeeStructure(db.Model):
    """Institutional course fee configuration per semester."""
    __tablename__ = 'fee_structures'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(20), default='2026-2027')
    total_fee = db.Column(db.Float, nullable=False, default=40000.0)
    due_date = db.Column(db.Date, nullable=False)

    student_fees = db.relationship('StudentFee', backref='fee_structure', lazy='dynamic')

    def __repr__(self):
        return f"<FeeStructure Course:{self.course_id} Sem:{self.semester} Amount:{self.total_fee}>"


class StudentFee(db.Model):
    """Ledger balance tracking per student for a given fee cycle."""
    __tablename__ = 'student_fees'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    fee_structure_id = db.Column(db.Integer, db.ForeignKey('fee_structures.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=40000.0)
    paid_amount = db.Column(db.Float, default=0.0)
    balance_amount = db.Column(db.Float, default=40000.0)
    status = db.Column(db.String(20), default='unpaid')  # 'paid', 'partial', 'unpaid'

    payments = db.relationship('FeePayment', backref='student_fee', lazy='dynamic', cascade='all, delete-orphan')

    def update_balance(self):
        total_paid = sum(p.amount_paid for p in self.payments)
        self.paid_amount = round(total_paid, 2)
        self.balance_amount = round(max(0.0, self.total_amount - self.paid_amount), 2)
        if self.balance_amount == 0.0:
            self.status = 'paid'
        elif self.paid_amount > 0.0:
            self.status = 'partial'
        else:
            self.status = 'unpaid'

    def __repr__(self):
        return f"<StudentFee Student:{self.student_id} Paid:{self.paid_amount} Bal:{self.balance_amount}>"


class FeePayment(db.Model):
    """Detailed fee installment transaction."""
    __tablename__ = 'fee_payments'

    id = db.Column(db.Integer, primary_key=True)
    student_fee_id = db.Column(db.Integer, db.ForeignKey('student_fees.id'), nullable=False)
    receipt_no = db.Column(db.String(50), unique=True, nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    payment_mode = db.Column(db.String(30), default='UPI')  # Cash, UPI, Net Banking, Cheque
    transaction_ref = db.Column(db.String(100))
    collected_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.String(255))

    def __repr__(self):
        return f"<FeePayment {self.receipt_no}: ₹{self.amount_paid}>"


class AuditLog(db.Model):
    """Security audit trail for tracking critical institutional modifications."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)       # 'STUDENT_CREATED', 'MARKS_UPDATED', 'FEE_PAID', 'LOGIN'
    entity_type = db.Column(db.String(50))                   # 'Student', 'Marks', 'FeePayment', 'User'
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog {self.action} by User:{self.user_id} at {self.timestamp}>"
