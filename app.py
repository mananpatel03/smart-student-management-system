import os
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort

from config import Config
from models import (
    db, User, Course, Subject, Student, Attendance, Exam, Marks,
    FeeStructure, StudentFee, FeePayment, AuditLog
)
from seed_data import seed_database

def create_app():
    """Application factory for Smart Student Management System."""
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # ---------------------------------------------------------
    # Context Processors & Helpers
    # ---------------------------------------------------------
    @app.context_processor
    def inject_global_vars():
        current_user = None
        if 'user_id' in session:
            current_user = db.session.get(User, session['user_id'])
        return {
            'current_user': current_user,
            'institute_name': app.config['INSTITUTE_NAME'],
            'institute_code': app.config['INSTITUTE_CODE'],
            'institute_address': app.config['INSTITUTE_ADDRESS'],
            'institute_phone': app.config['INSTITUTE_PHONE'],
            'institute_email': app.config['INSTITUTE_EMAIL'],
            'attendance_threshold': app.config['ATTENDANCE_THRESHOLD'],
            'now': datetime.utcnow()
        }

    def log_audit(action, entity_type, entity_id, details):
        """Helper to append an audit log entry."""
        try:
            user_id = session.get('user_id')
            ip = request.remote_addr or '127.0.0.1'
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                ip_address=ip
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Audit log error: {e}")

    # ---------------------------------------------------------
    # Authorization Decorators
    # ---------------------------------------------------------
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function

    def roles_accepted(*roles):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('login', next=request.url))
                user_role = session.get('role')
                if user_role not in roles and 'admin' not in roles:
                    flash('You are not authorized to view or perform this action.', 'danger')
                    return redirect(url_for('dashboard'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    # ---------------------------------------------------------
    # Authentication Routes (Module 6)
    # ---------------------------------------------------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            user = User.query.filter_by(username=username).first()
            if user and user.is_active and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                session['full_name'] = user.full_name

                log_audit('USER_LOGIN', 'User', user.id, f"User {user.username} logged in successfully.")
                flash(f"Welcome back, {user.full_name}!", 'success')

                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid username, password, or account inactive.', 'danger')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        if 'user_id' in session:
            log_audit('USER_LOGOUT', 'User', session['user_id'], f"User {session.get('username')} logged out.")
            session.clear()
            flash('You have been logged out successfully.', 'info')
        return redirect(url_for('login'))

    # ---------------------------------------------------------
    # Smart Dashboard & Analytics (Module 5)
    # ---------------------------------------------------------
    @app.route('/')
    @app.route('/dashboard')
    @login_required
    def dashboard():
        user_role = session.get('role')

        # If student logs in, redirect to their personalized 360-view
        if user_role == 'student':
            student = Student.query.filter_by(user_id=session['user_id']).first()
            if student:
                return redirect(url_for('student_view', student_id=student.id))

        total_students = Student.query.count()
        active_students = Student.query.filter_by(status='active').count()
        total_courses = Course.query.count()

        # Overall Attendance calculation
        total_attendance_records = Attendance.query.count()
        present_attendance_records = Attendance.query.filter(Attendance.status.in_(['present', 'leave'])).count()
        overall_attendance_pct = round((present_attendance_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 100.0

        # Fee Statistics
        all_fees = StudentFee.query.all()
        total_fee_expected = sum(f.total_amount for f in all_fees)
        total_fee_collected = sum(f.paid_amount for f in all_fees)
        total_fee_pending = sum(f.balance_amount for f in all_fees)

        # Smart Analytics: Early-Warning At-Risk Students
        # Flag if: overall attendance < 75% OR has failed in >= 1 subject
        at_risk_students = []
        students = Student.query.filter_by(status='active').all()
        for s in students:
            att_pct = s.calculate_attendance_percentage()
            failed_marks = Marks.query.filter_by(student_id=s.id, status='fail').all()
            
            reasons = []
            if att_pct < app.config['ATTENDANCE_THRESHOLD']:
                reasons.append(f"Low Attendance ({att_pct}%)")
            if failed_marks:
                failed_subjects = [m.subject.code for m in failed_marks]
                reasons.append(f"Failed in: {', '.join(failed_subjects)}")

            if reasons:
                at_risk_students.append({
                    'student': s,
                    'attendance_pct': att_pct,
                    'reasons': reasons
                })

        # Recent activities from Audit Log
        recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()

        return render_template(
            'dashboard.html',
            total_students=total_students,
            active_students=active_students,
            total_courses=total_courses,
            overall_attendance_pct=overall_attendance_pct,
            total_fee_expected=total_fee_expected,
            total_fee_collected=total_fee_collected,
            total_fee_pending=total_fee_pending,
            at_risk_students=at_risk_students,
            recent_logs=recent_logs
        )

    # API endpoints for Chart.js Dashboards
    @app.route('/api/analytics/course-distribution')
    @login_required
    def api_course_distribution():
        courses = Course.query.all()
        labels = [c.code for c in courses]
        data = [c.students.count() for c in courses]
        return jsonify({'labels': labels, 'data': data})

    @app.route('/api/analytics/attendance-trend')
    @login_required
    def api_attendance_trend():
        # Get past 10 active dates
        distinct_dates = db.session.query(Attendance.date).distinct().order_by(Attendance.date.desc()).limit(10).all()
        distinct_dates = sorted([d[0] for d in distinct_dates])
        
        labels = [d.strftime('%d %b') for d in distinct_dates]
        data = []
        for d in distinct_dates:
            total = Attendance.query.filter_by(date=d).count()
            present = Attendance.query.filter_by(date=d).filter(Attendance.status.in_(['present', 'leave'])).count()
            pct = round((present / total * 100), 1) if total > 0 else 100.0
            data.append(pct)

        return jsonify({'labels': labels, 'data': data})

    @app.route('/api/analytics/fee-summary')
    @login_required
    def api_fee_summary():
        paid_count = StudentFee.query.filter_by(status='paid').count()
        partial_count = StudentFee.query.filter_by(status='partial').count()
        unpaid_count = StudentFee.query.filter_by(status='unpaid').count()
        return jsonify({
            'labels': ['Fully Paid', 'Partially Paid', 'Unpaid'],
            'data': [paid_count, partial_count, unpaid_count]
        })

    # ---------------------------------------------------------
    # Module 1: Student Management
    # ---------------------------------------------------------
    @app.route('/students')
    @login_required
    @roles_accepted('admin', 'teacher', 'accountant')
    def students_list():
        query = Student.query

        search = request.args.get('search', '').strip()
        course_id = request.args.get('course_id')
        semester = request.args.get('semester')
        status = request.args.get('status')

        if search:
            query = query.filter(
                (Student.first_name.ilike(f"%{search}%")) |
                (Student.last_name.ilike(f"%{search}%")) |
                (Student.student_id.ilike(f"%{search}%")) |
                (Student.email.ilike(f"%{search}%"))
            )
        if course_id:
            query = query.filter_by(course_id=course_id)
        if semester:
            query = query.filter_by(semester=int(semester))
        if status:
            query = query.filter_by(status=status)

        students = query.order_by(Student.student_id.asc()).all()
        courses = Course.query.all()

        return render_template('students/list.html', students=students, courses=courses, search=search, selected_course=course_id, selected_sem=semester, selected_status=status)

    @app.route('/students/add', methods=['GET', 'POST'])
    @login_required
    @roles_accepted('admin')
    def student_add():
        courses = Course.query.all()
        if request.method == 'POST':
            student_id = request.form.get('student_id', '').strip().upper()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            course_id = int(request.form.get('course_id'))
            semester = int(request.form.get('semester', 1))
            guardian_name = request.form.get('guardian_name', '').strip()
            guardian_phone = request.form.get('guardian_phone', '').strip()
            address = request.form.get('address', '').strip()

            # Validations
            if Student.query.filter_by(student_id=student_id).first():
                flash(f"Error: Student ID '{student_id}' already exists!", 'danger')
                return render_template('students/form.html', courses=courses, form_data=request.form)

            if Student.query.filter_by(email=email).first() or User.query.filter_by(email=email).first():
                flash(f"Error: Email '{email}' is already registered!", 'danger')
                return render_template('students/form.html', courses=courses, form_data=request.form)

            # Create User Account for the student
            username = email.split('@')[0].replace('.', '_')
            if User.query.filter_by(username=username).first():
                username = f"{username}_{student_id.lower()}"

            user = User(
                username=username,
                role='student',
                email=email,
                full_name=f"{first_name} {last_name}"
            )
            user.set_password('student123')
            db.session.add(user)
            db.session.flush()

            # Create Student Record
            student = Student(
                student_id=student_id,
                user_id=user.id,
                course_id=course_id,
                semester=semester,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address=address,
                enrollment_date=date.today(),
                status='active',
                guardian_name=guardian_name,
                guardian_phone=guardian_phone
            )
            db.session.add(student)
            db.session.flush()

            # Auto-assign fee structure if exists
            fee_struct = FeeStructure.query.filter_by(course_id=course_id, semester=semester).first()
            if fee_struct:
                stu_fee = StudentFee(
                    student_id=student.id,
                    fee_structure_id=fee_struct.id,
                    total_amount=fee_struct.total_fee,
                    paid_amount=0.0,
                    balance_amount=fee_struct.total_fee,
                    status='unpaid'
                )
                db.session.add(stu_fee)

            db.session.commit()
            log_audit('STUDENT_CREATED', 'Student', student.id, f"Added student {student.student_id} ({student.full_name}) with login '{username}'")
            flash(f"Student {first_name} {last_name} enrolled successfully! Default password is 'student123'.", 'success')
            return redirect(url_for('students_list'))

        return render_template('students/form.html', courses=courses, form_data={}, is_edit=False)

    @app.route('/students/edit/<int:student_id>', methods=['GET', 'POST'])
    @login_required
    @roles_accepted('admin')
    def student_edit(student_id):
        student = Student.query.get_or_404(student_id)
        courses = Course.query.all()

        if request.method == 'POST':
            student.first_name = request.form.get('first_name', '').strip()
            student.last_name = request.form.get('last_name', '').strip()
            student.phone = request.form.get('phone', '').strip()
            student.course_id = int(request.form.get('course_id'))
            student.semester = int(request.form.get('semester'))
            student.guardian_name = request.form.get('guardian_name', '').strip()
            student.guardian_phone = request.form.get('guardian_phone', '').strip()
            student.address = request.form.get('address', '').strip()
            student.status = request.form.get('status', 'active')

            if student.user_account:
                student.user_account.full_name = student.full_name
                student.user_account.is_active = (student.status == 'active')

            db.session.commit()
            log_audit('STUDENT_UPDATED', 'Student', student.id, f"Updated profile for student {student.student_id}")
            flash('Student profile updated successfully.', 'success')
            return redirect(url_for('student_view', student_id=student.id))

        return render_template('students/form.html', courses=courses, student=student, is_edit=True)

    @app.route('/students/view/<int:student_id>')
    @login_required
    def student_view(student_id):
        student = Student.query.get_or_404(student_id)

        # Authorization: Students can only view their own profile
        if session.get('role') == 'student':
            logged_in_user = db.session.get(User, session['user_id'])
            if not logged_in_user.student_profile or logged_in_user.student_profile.id != student.id:
                flash('You are not authorized to view other students’ records.', 'danger')
                return redirect(url_for('dashboard'))

        # Subject-wise attendance breakdown
        subjects = Subject.query.filter_by(course_id=student.course_id, semester=student.semester).all()
        attendance_stats = []
        for sub in subjects:
            total_classes = Attendance.query.filter_by(student_id=student.id, subject_id=sub.id).count()
            attended = Attendance.query.filter_by(student_id=student.id, subject_id=sub.id).filter(Attendance.status.in_(['present', 'leave'])).count()
            pct = round((attended / total_classes * 100), 1) if total_classes > 0 else 100.0
            attendance_stats.append({
                'subject': sub,
                'total': total_classes,
                'attended': attended,
                'pct': pct,
                'is_defaulter': pct < app.config['ATTENDANCE_THRESHOLD']
            })

        # Academic marks history
        marks_records = Marks.query.filter_by(student_id=student.id).all()

        # Fee ledger & payments
        fee_records = StudentFee.query.filter_by(student_id=student.id).all()

        overall_attendance = student.calculate_attendance_percentage()

        return render_template(
            'students/view.html',
            student=student,
            attendance_stats=attendance_stats,
            overall_attendance=overall_attendance,
            marks_records=marks_records,
            fee_records=fee_records
        )

    @app.route('/students/toggle-status/<int:student_id>')
    @login_required
    @roles_accepted('admin')
    def student_toggle_status(student_id):
        student = Student.query.get_or_404(student_id)
        new_status = 'inactive' if student.status == 'active' else 'active'
        student.status = new_status
        if student.user_account:
            student.user_account.is_active = (new_status == 'active')
        db.session.commit()

        log_audit('STUDENT_STATUS_CHANGED', 'Student', student.id, f"Changed status of {student.student_id} to {new_status}")
        flash(f"Student {student.student_id} is now {new_status}.", 'info')
        return redirect(request.referrer or url_for('students_list'))

    # ---------------------------------------------------------
    # Module 2: Attendance Management
    # ---------------------------------------------------------
    @app.route('/attendance')
    @login_required
    @roles_accepted('admin', 'teacher')
    def attendance_overview():
        courses = Course.query.all()
        subjects = Subject.query.all()
        return render_template('attendance/overview.html', courses=courses, subjects=subjects)

    @app.route('/attendance/mark', methods=['GET', 'POST'])
    @login_required
    @roles_accepted('admin', 'teacher')
    def attendance_mark():
        courses = Course.query.all()
        subjects = Subject.query.all()

        selected_course = request.args.get('course_id')
        selected_sem = request.args.get('semester')
        selected_subject = request.args.get('subject_id')
        selected_date = request.args.get('date', date.today().isoformat())

        students = []
        existing_attendance = {}
        if selected_course and selected_sem and selected_subject:
            students = Student.query.filter_by(course_id=int(selected_course), semester=int(selected_sem), status='active').order_by(Student.student_id.asc()).all()
            
            # Fetch existing records for this subject and date if already marked
            records = Attendance.query.filter_by(
                subject_id=int(selected_subject),
                date=datetime.strptime(selected_date, '%Y-%m-%d').date()
            ).all()
            for r in records:
                existing_attendance[r.student_id] = r.status

        if request.method == 'POST':
            subject_id = int(request.form.get('subject_id'))
            att_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            remarks = request.form.get('remarks', 'Lecture session')

            student_ids = request.form.getlist('student_ids')
            for s_id in student_ids:
                s_id_int = int(s_id)
                status = request.form.get(f'status_{s_id_int}', 'present')

                record = Attendance.query.filter_by(
                    student_id=s_id_int,
                    subject_id=subject_id,
                    date=att_date
                ).first()

                if record:
                    record.status = status
                    record.remarks = remarks
                    record.marked_by = session.get('user_id')
                else:
                    record = Attendance(
                        student_id=s_id_int,
                        subject_id=subject_id,
                        date=att_date,
                        status=status,
                        remarks=remarks,
                        marked_by=session.get('user_id')
                    )
                    db.session.add(record)

            db.session.commit()
            log_audit('ATTENDANCE_LOGGED', 'Attendance', subject_id, f"Marked attendance for Subject ID {subject_id} on {att_date} for {len(student_ids)} students.")
            flash(f"Attendance recorded successfully for {len(student_ids)} students on {att_date}!", 'success')
            return redirect(url_for('attendance_mark', course_id=selected_course, semester=selected_sem, subject_id=selected_subject, date=selected_date))

        return render_template(
            'attendance/mark.html',
            courses=courses,
            subjects=subjects,
            students=students,
            selected_course=selected_course,
            selected_sem=selected_sem,
            selected_subject=selected_subject,
            selected_date=selected_date,
            existing_attendance=existing_attendance
        )

    @app.route('/attendance/report')
    @login_required
    @roles_accepted('admin', 'teacher', 'accountant')
    def attendance_report():
        courses = Course.query.all()
        selected_course = request.args.get('course_id', type=int)
        selected_sem = request.args.get('semester', type=int)

        report_data = []
        subjects = []
        if selected_course and selected_sem:
            subjects = Subject.query.filter_by(course_id=selected_course, semester=selected_sem).all()
            students = Student.query.filter_by(course_id=selected_course, semester=selected_sem, status='active').all()

            for s in students:
                sub_stats = {}
                total_classes_all = 0
                attended_classes_all = 0

                for sub in subjects:
                    total_c = Attendance.query.filter_by(student_id=s.id, subject_id=sub.id).count()
                    att_c = Attendance.query.filter_by(student_id=s.id, subject_id=sub.id).filter(Attendance.status.in_(['present', 'leave'])).count()
                    pct = round((att_c / total_c * 100), 1) if total_c > 0 else 100.0

                    total_classes_all += total_c
                    attended_classes_all += att_c
                    sub_stats[sub.id] = {'attended': att_c, 'total': total_c, 'pct': pct}

                overall_pct = round((attended_classes_all / total_classes_all * 100), 1) if total_classes_all > 0 else 100.0
                report_data.append({
                    'student': s,
                    'subject_stats': sub_stats,
                    'overall_pct': overall_pct,
                    'is_defaulter': overall_pct < app.config['ATTENDANCE_THRESHOLD']
                })

        return render_template(
            'attendance/report.html',
            courses=courses,
            selected_course=selected_course,
            selected_sem=selected_sem,
            subjects=subjects,
            report_data=report_data
        )

    @app.route('/attendance/defaulters')
    @login_required
    @roles_accepted('admin', 'teacher')
    def attendance_defaulters():
        defaulters = []
        students = Student.query.filter_by(status='active').all()
        for s in students:
            pct = s.calculate_attendance_percentage()
            if pct < app.config['ATTENDANCE_THRESHOLD']:
                defaulters.append({
                    'student': s,
                    'pct': pct,
                    'course': s.course.code,
                    'semester': s.semester
                })

        return render_template('attendance/defaulters.html', defaulters=defaulters)

    # ---------------------------------------------------------
    # Module 3: Marks & Results
    # ---------------------------------------------------------
    @app.route('/marks')
    @login_required
    @roles_accepted('admin', 'teacher')
    def marks_overview():
        exams = Exam.query.all()
        subjects = Subject.query.all()
        return render_template('marks/overview.html', exams=exams, subjects=subjects)

    @app.route('/marks/entry', methods=['GET', 'POST'])
    @login_required
    @roles_accepted('admin', 'teacher')
    def marks_entry():
        exams = Exam.query.all()
        courses = Course.query.all()
        subjects = Subject.query.all()

        selected_exam = request.args.get('exam_id', type=int)
        selected_course = request.args.get('course_id', type=int)
        selected_sem = request.args.get('semester', type=int)
        selected_subject = request.args.get('subject_id', type=int)

        students = []
        existing_marks = {}
        subject_obj = None

        if selected_exam and selected_course and selected_sem and selected_subject:
            subject_obj = db.session.get(Subject, selected_subject)
            students = Student.query.filter_by(course_id=selected_course, semester=selected_sem, status='active').order_by(Student.student_id.asc()).all()

            records = Marks.query.filter_by(exam_id=selected_exam, subject_id=selected_subject).all()
            for r in records:
                existing_marks[r.student_id] = r

        if request.method == 'POST':
            exam_id = int(request.form.get('exam_id'))
            subject_id = int(request.form.get('subject_id'))
            sub = db.session.get(Subject, subject_id)

            student_ids = request.form.getlist('student_ids')
            for s_id in student_ids:
                s_id_int = int(s_id)
                internal = float(request.form.get(f'internal_{s_id_int}', 0.0) or 0.0)
                external = float(request.form.get(f'external_{s_id_int}', 0.0) or 0.0)

                # Clamp values to maximums
                internal = min(sub.max_internal, max(0.0, internal))
                external = min(sub.max_external, max(0.0, external))

                mark_record = Marks.query.filter_by(exam_id=exam_id, student_id=s_id_int, subject_id=subject_id).first()
                if not mark_record:
                    mark_record = Marks(
                        exam_id=exam_id,
                        student_id=s_id_int,
                        subject_id=subject_id,
                        entered_by=session.get('user_id')
                    )
                    db.session.add(mark_record)

                mark_record.internal_marks = internal
                mark_record.external_marks = external
                mark_record.compute_result(max_internal=sub.max_internal, max_external=sub.max_external)

            db.session.commit()
            log_audit('MARKS_ENTERED', 'Marks', subject_id, f"Saved evaluation marks for Subject {sub.code} ({len(student_ids)} students).")
            flash(f"Marks calculated and recorded successfully for {len(student_ids)} students!", 'success')
            return redirect(url_for('marks_entry', exam_id=exam_id, course_id=selected_course, semester=selected_sem, subject_id=subject_id))

        return render_template(
            'marks/entry.html',
            exams=exams,
            courses=courses,
            subjects=subjects,
            students=students,
            subject_obj=subject_obj,
            selected_exam=selected_exam,
            selected_course=selected_course,
            selected_sem=selected_sem,
            selected_subject=selected_subject,
            existing_marks=existing_marks
        )

    @app.route('/marks/report-card/<int:student_id>/<int:exam_id>')
    @login_required
    def marks_report_card(student_id, exam_id):
        student = Student.query.get_or_404(student_id)
        exam = Exam.query.get_or_404(exam_id)

        # Check student access permission
        if session.get('role') == 'student':
            logged_in_user = db.session.get(User, session['user_id'])
            if not logged_in_user.student_profile or logged_in_user.student_profile.id != student.id:
                flash('You are not authorized to view this report card.', 'danger')
                return redirect(url_for('dashboard'))

        marks = Marks.query.filter_by(student_id=student.id, exam_id=exam.id).all()
        
        total_obtained = sum(m.total_marks for m in marks)
        total_max = sum(m.subject.max_total for m in marks)
        aggregate_pct = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0.0
        
        has_failed = any(m.status == 'fail' for m in marks)
        final_result = 'FAIL' if has_failed else 'PASS'

        return render_template(
            'marks/report_card.html',
            student=student,
            exam=exam,
            marks=marks,
            total_obtained=total_obtained,
            total_max=total_max,
            aggregate_pct=aggregate_pct,
            final_result=final_result
        )

    # ---------------------------------------------------------
    # Module 4: Fee Management
    # ---------------------------------------------------------
    @app.route('/fees')
    @login_required
    @roles_accepted('admin', 'accountant')
    def fees_list():
        status_filter = request.args.get('status')
        course_filter = request.args.get('course_id', type=int)

        query = StudentFee.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        if course_filter:
            query = query.join(Student).filter(Student.course_id == course_filter)

        fees = query.all()
        courses = Course.query.all()

        total_collected = sum(f.paid_amount for f in fees)
        total_pending = sum(f.balance_amount for f in fees)

        return render_template(
            'fees/manage.html',
            fees=fees,
            courses=courses,
            selected_status=status_filter,
            selected_course=course_filter,
            total_collected=total_collected,
            total_pending=total_pending
        )

    @app.route('/fees/collect/<int:student_fee_id>', methods=['GET', 'POST'])
    @login_required
    @roles_accepted('admin', 'accountant')
    def fee_collect(student_fee_id):
        student_fee = StudentFee.query.get_or_404(student_fee_id)

        if request.method == 'POST':
            amount = float(request.form.get('amount_paid', 0.0))
            payment_mode = request.form.get('payment_mode', 'UPI')
            transaction_ref = request.form.get('transaction_ref', '').strip()
            notes = request.form.get('notes', 'Tuition installment')

            if amount <= 0:
                flash('Payment amount must be greater than zero.', 'danger')
                return render_template('fees/collect.html', student_fee=student_fee)

            if amount > student_fee.balance_amount:
                flash(f"Amount entered (₹{amount}) exceeds outstanding balance (₹{student_fee.balance_amount})!", 'danger')
                return render_template('fees/collect.html', student_fee=student_fee)

            # Generate unique receipt number: REC-YYYYMMDD-XXXX
            today_str = datetime.today().strftime('%Y%m%d')
            count_today = FeePayment.query.filter(FeePayment.receipt_no.like(f"REC-{today_str}-%")).count() + 1
            receipt_no = f"REC-{today_str}-{count_today:04d}"

            payment = FeePayment(
                student_fee_id=student_fee.id,
                receipt_no=receipt_no,
                amount_paid=amount,
                payment_date=date.today(),
                payment_mode=payment_mode,
                transaction_ref=transaction_ref,
                collected_by=session.get('user_id'),
                notes=notes
            )
            db.session.add(payment)
            student_fee.update_balance()
            db.session.commit()

            log_audit('FEE_PAYMENT_COLLECTED', 'FeePayment', payment.id, f"Collected ₹{amount} from {student_fee.student.student_id} ({receipt_no}). Balance remaining: ₹{student_fee.balance_amount}")
            flash(f"Payment of ₹{amount} recorded successfully! Receipt: {receipt_no}", 'success')
            return redirect(url_for('fee_receipt', receipt_no=receipt_no))

        return render_template('fees/collect.html', student_fee=student_fee)

    @app.route('/fees/receipt/<string:receipt_no>')
    @login_required
    def fee_receipt(receipt_no):
        payment = FeePayment.query.filter_by(receipt_no=receipt_no).first_or_404()
        student_fee = payment.student_fee
        student = student_fee.student

        # Check student access permission
        if session.get('role') == 'student':
            logged_in_user = db.session.get(User, session['user_id'])
            if not logged_in_user.student_profile or logged_in_user.student_profile.id != student.id:
                flash('You are not authorized to view this receipt.', 'danger')
                return redirect(url_for('dashboard'))

        collector = db.session.get(User, payment.collected_by) if payment.collected_by else None

        return render_template(
            'fees/receipt.html',
            payment=payment,
            student_fee=student_fee,
            student=student,
            collector=collector
        )

    # ---------------------------------------------------------
    # Module 6: Security & Audit Logs
    # ---------------------------------------------------------
    @app.route('/audit-logs')
    @login_required
    @roles_accepted('admin')
    def audit_logs():
        logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(150).all()
        return render_template('audit/logs.html', logs=logs)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_database()
    print("\n* SSMS Server starting on http://127.0.0.1:5000 ...")
    app.run(debug=True, host='127.0.0.1', port=5000)
