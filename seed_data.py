from datetime import date, datetime, timedelta
from models import db, User, Course, Subject, Student, Attendance, Exam, Marks, FeeStructure, StudentFee, FeePayment, AuditLog

def seed_database():
    """Populates the database with realistic sample records if empty."""
    # Check if admin already exists
    if User.query.filter_by(username='admin').first():
        print("Database already seeded. Skipping initial seeding.")
        return

    print("Seeding database with comprehensive demo records...")

    # 1. Create Users
    admin = User(username='admin', role='admin', email='admin@aite-edu.in', full_name='Dr. Arvind Kulkarni (Principal)')
    admin.set_password('admin123')

    teacher1 = User(username='sharma_prof', role='teacher', email='r.sharma@aite-edu.in', full_name='Prof. Rajesh Sharma (HOD CE)')
    teacher1.set_password('teacher123')

    teacher2 = User(username='verma_prof', role='teacher', email='p.verma@aite-edu.in', full_name='Prof. Priya Verma (Asst. Prof)')
    teacher2.set_password('teacher123')

    accountant = User(username='accountant', role='accountant', email='accounts@aite-edu.in', full_name='Suresh Patel (Bursar/Accountant)')
    accountant.set_password('account123')

    db.session.add_all([admin, teacher1, teacher2, accountant])
    db.session.flush()

    # 2. Create Courses
    c_ce = Course(code='BTECH-CE', name='B.Tech Computer Engineering', description='Undergraduate engineering program in computing systems.', duration_semesters=8)
    c_it = Course(code='BTECH-IT', name='B.Tech Information Technology', description='Software design, networking, and cloud applications.', duration_semesters=8)
    c_ai = Course(code='BTECH-AI', name='B.Tech Artificial Intelligence & Data Science', description='Machine learning, deep learning, and big data architectures.', duration_semesters=8)

    db.session.add_all([c_ce, c_it, c_ai])
    db.session.flush()

    # 3. Create Subjects for Semester 4 (BTECH-CE)
    s1 = Subject(code='CS401', name='Database Management Systems', course_id=c_ce.id, semester=4, credits=4, max_internal=30, max_external=70, pass_marks=40)
    s2 = Subject(code='CS402', name='Operating Systems', course_id=c_ce.id, semester=4, credits=4, max_internal=30, max_external=70, pass_marks=40)
    s3 = Subject(code='CS403', name='Computer Networks', course_id=c_ce.id, semester=4, credits=4, max_internal=30, max_external=70, pass_marks=40)
    s4 = Subject(code='CS404', name='Design & Analysis of Algorithms', course_id=c_ce.id, semester=4, credits=4, max_internal=30, max_external=70, pass_marks=40)

    db.session.add_all([s1, s2, s3, s4])
    db.session.flush()

    # 4. Create Students & Link Student User Accounts
    student_specs = [
        {
            'username': 'rohan_mehta', 'email': 'rohan.mehta@student.aite.in', 'name': 'Rohan Mehta',
            'id': 'STU2026001', 'phone': '9820112233', 'guardian': 'Sanjay Mehta', 'g_phone': '9820199887',
            'addr': 'Flat 402, Green Glen, Mumbai', 'sem': 4, 'course': c_ce.id
        },
        {
            'username': 'ananya_iyer', 'email': 'ananya.iyer@student.aite.in', 'name': 'Ananya Iyer',
            'id': 'STU2026002', 'phone': '9819223344', 'guardian': 'Ramachandran Iyer', 'g_phone': '9819288776',
            'addr': '14 Matunga East, Mumbai', 'sem': 4, 'course': c_ce.id
        },
        {
            'username': 'vikram_singh', 'email': 'vikram.singh@student.aite.in', 'name': 'Vikram Singh',
            'id': 'STU2026003', 'phone': '9833445566', 'guardian': 'Mahendra Singh', 'g_phone': '9833477665',
            'addr': 'B-12 Powai Heights, Mumbai', 'sem': 4, 'course': c_ce.id
        },
        {
            'username': 'sneha_patil', 'email': 'sneha.patil@student.aite.in', 'name': 'Sneha Patil',
            'id': 'STU2026004', 'phone': '9867556677', 'guardian': 'Anil Patil', 'g_phone': '9867544332',
            'addr': '704 Thane West, Thane', 'sem': 4, 'course': c_ce.id
        },
        {
            'username': 'aarav_gupta', 'email': 'aarav.gupta@student.aite.in', 'name': 'Aarav Gupta',
            'id': 'STU2026005', 'phone': '9870667788', 'guardian': 'Vivek Gupta', 'g_phone': '9870655443',
            'addr': 'Tower 3, Hiranandani Estate, Thane', 'sem': 4, 'course': c_ce.id
        }
    ]

    students = []
    for spec in student_specs:
        s_user = User(
            username=spec['username'],
            role='student',
            email=spec['email'],
            full_name=spec['name']
        )
        s_user.set_password('student123')
        db.session.add(s_user)
        db.session.flush()

        first_name, last_name = spec['name'].split(' ', 1)
        student = Student(
            student_id=spec['id'],
            user_id=s_user.id,
            course_id=spec['course'],
            semester=spec['sem'],
            first_name=first_name,
            last_name=last_name,
            email=spec['email'],
            phone=spec['phone'],
            address=spec['addr'],
            enrollment_date=date(2024, 8, 1),
            status='active',
            guardian_name=spec['guardian'],
            guardian_phone=spec['g_phone']
        )
        db.session.add(student)
        students.append(student)

    db.session.flush()

    # 5. Seed Attendance across 12 sessions per subject
    # Attendance distribution:
    # Rohan: ~85%, Ananya: ~95%, Vikram: ~60% (Below 75% threshold!), Sneha: ~90%, Aarav: ~80%
    subjects = [s1, s2, s3, s4]
    today = date.today()
    session_dates = [today - timedelta(days=i) for i in range(16, 0, -1) if (today - timedelta(days=i)).weekday() < 5][:12]

    for sub_idx, sub in enumerate(subjects):
        for day_idx, att_date in enumerate(session_dates):
            # Rohan: misses 2 sessions
            s1_status = 'absent' if day_idx in [2, 7] else 'present'
            # Ananya: misses 0 sessions
            s2_status = 'present'
            # Vikram: misses 5 sessions (Demonstrates Defaulter Alert!)
            s3_status = 'absent' if day_idx in [1, 3, 5, 8, 10] else 'present'
            # Sneha: misses 1 session (approved leave)
            s4_status = 'leave' if day_idx == 4 else 'present'
            # Aarav: misses 2 sessions
            s5_status = 'absent' if day_idx in [0, 6] else 'present'

            statuses = [s1_status, s2_status, s3_status, s4_status, s5_status]

            for st_idx, stu in enumerate(students):
                att = Attendance(
                    student_id=stu.id,
                    subject_id=sub.id,
                    date=att_date,
                    status=statuses[st_idx],
                    remarks='Regular session' if statuses[st_idx] == 'present' else ('Medical slip' if statuses[st_idx] == 'leave' else 'Unexcused'),
                    marked_by=teacher1.id if sub_idx % 2 == 0 else teacher2.id
                )
                db.session.add(att)

    # 6. Seed Exam and Marks
    midterm = Exam(name='Mid-Term Evaluation 2026', exam_type='Mid-Term', academic_year='2026-2027', semester=4)
    db.session.add(midterm)
    db.session.flush()

    # Sample performance profiles (Internal max: 30, External max: 70, Total max: 100)
    marks_data = [
        # Rohan (Solid Good student)
        [students[0], [(s1, 26, 58), (s2, 24, 52), (s3, 27, 60), (s4, 25, 55)]],
        # Ananya (Outstanding Top Ranker)
        [students[1], [(s1, 29, 66), (s2, 28, 64), (s3, 30, 68), (s4, 29, 65)]],
        # Vikram (At-Risk in OS CS402)
        [students[2], [(s1, 18, 38), (s2, 10, 24), (s3, 19, 42), (s4, 16, 36)]],
        # Sneha (Very Good student)
        [students[3], [(s1, 25, 56), (s2, 26, 54), (s3, 24, 58), (s4, 27, 60)]],
        # Aarav (Average / Above Average)
        [students[4], [(s1, 22, 48), (s2, 20, 46), (s3, 23, 50), (s4, 21, 45)]]
    ]

    for student_entry in marks_data:
        stu, sub_scores = student_entry
        for sub, internal, external in sub_scores:
            m = Marks(
                exam_id=midterm.id,
                student_id=stu.id,
                subject_id=sub.id,
                internal_marks=internal,
                external_marks=external,
                entered_by=teacher1.id
            )
            m.compute_result(max_internal=sub.max_internal, max_external=sub.max_external)
            db.session.add(m)

    # 7. Seed Fee Structures & Payments
    fee_struct = FeeStructure(
        course_id=c_ce.id,
        semester=4,
        academic_year='2026-2027',
        total_fee=40000.0,
        due_date=date.today() + timedelta(days=20)
    )
    db.session.add(fee_struct)
    db.session.flush()

    # Student Fees Ledger
    # Rohan: Paid ₹25,000 (Balance ₹15,000 - Partial)
    # Ananya: Paid ₹40,000 (Balance ₹0 - Paid)
    # Vikram: Paid ₹20,000 (Balance ₹20,000 - Partial)
    # Sneha: Paid ₹40,000 (Balance ₹0 - Paid)
    # Aarav: Paid ₹0 (Balance ₹40,000 - Unpaid)

    fee_configs = [
        (students[0], [(15000, 'UPI', 'UPI-TXN-882103', date.today() - timedelta(days=25)),
                       (10000, 'Net Banking', 'HDFC-NB-90412', date.today() - timedelta(days=10))]),
        (students[1], [(40000, 'Net Banking', 'ICICI-NB-55412', date.today() - timedelta(days=30))]),
        (students[2], [(20000, 'UPI', 'GPAY-TXN-44129', date.today() - timedelta(days=15))]),
        (students[3], [(20000, 'Cheque', 'CHQ-889102-SBI', date.today() - timedelta(days=28)),
                       (20000, 'Cash', 'CASH-REC-112', date.today() - timedelta(days=5))]),
        (students[4], [])  # Unpaid
    ]

    receipt_counter = 1001
    for stu, payments in fee_configs:
        sf = StudentFee(
            student_id=stu.id,
            fee_structure_id=fee_struct.id,
            total_amount=fee_struct.total_fee,
            paid_amount=0.0,
            balance_amount=fee_struct.total_fee,
            status='unpaid'
        )
        db.session.add(sf)
        db.session.flush()

        for amt, mode, ref, pay_date in payments:
            rec_no = f"REC-2026-{receipt_counter}"
            receipt_counter += 1
            pmt = FeePayment(
                student_fee_id=sf.id,
                receipt_no=rec_no,
                amount_paid=amt,
                payment_date=pay_date,
                payment_mode=mode,
                transaction_ref=ref,
                collected_by=accountant.id,
                notes=f"Term installment payment for {stu.first_name}"
            )
            db.session.add(pmt)

        sf.update_balance()

    # 8. Seed Initial Audit Logs
    audit1 = AuditLog(
        user_id=admin.id,
        action='SYSTEM_INITIALIZED',
        entity_type='System',
        entity_id=1,
        details='Initial academic session 2026-2027 configured with 3 departments.',
        ip_address='127.0.0.1'
    )
    audit2 = AuditLog(
        user_id=teacher1.id,
        action='MARKS_RECORDED',
        entity_type='Marks',
        entity_id=midterm.id,
        details='Mid-term evaluation scores posted for B.Tech CE Semester 4.',
        ip_address='127.0.0.1'
    )
    audit3 = AuditLog(
        user_id=accountant.id,
        action='FEE_PAYMENT_COLLECTED',
        entity_type='FeePayment',
        entity_id=1,
        details='Collected fee installment of ₹25,000 for student STU2026001 (Rohan Mehta).',
        ip_address='127.0.0.1'
    )
    db.session.add_all([audit1, audit2, audit3])

    db.session.commit()
    print("Database seeding completed successfully with 5 students, attendance, marks, fees, and audit records!")
