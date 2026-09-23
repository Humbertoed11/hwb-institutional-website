"""
SigmaFidelity™ SigmaAcademy™ B2B Training & Compliance LMS Blueprint
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect & mbB) & Silas Sync (VP of CRM)
Permanent Approval Authority: Humberto Dominguez (CEO)
"""

import os
import uuid
import json
import datetime
from flask import Blueprint, request, jsonify, render_template, current_app, redirect, url_for, abort
from core.services.database import get_db

academy_bp = Blueprint('academy', __name__)


def serialize_db_row(row):
    if not row:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime.date, datetime.datetime)):
            d[k] = v.isoformat()
        elif hasattr(v, '__str__') and 'Decimal' in str(type(v)):
            d[k] = float(v)
    return d


# ==============================================================================
# 1.0 PUBLIC & WEB INTERFACE ROUTES
# ==============================================================================

@academy_bp.route('/academy', methods=['GET'])
def academy_catalog():
    """Renders the SigmaAcademy Course Catalog & Training Portal."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    courses = []
    packages = []
    certified_count = 0
    active_tenants = 0
    try:
        with conn.cursor() as cur:
            try:
                cur.execute('''
                    SELECT 
                        c.id, c.course_code, c.title, c.category, c.regulatory_standard,
                        c.description, c.estimated_minutes, c.renewal_months, c.badge_icon,
                        COUNT(DISTINCT m.id) as module_count,
                        COUNT(DISTINCT q.id) as question_count
                    FROM "AcademyCourses" c
                    LEFT JOIN "AcademyCourseModules" m ON m.course_id = c.id
                    LEFT JOIN "AcademyQuizQuestions" q ON q.course_id = c.id
                    GROUP BY c.id
                    ORDER BY c.id ASC;
                ''')
                courses = [serialize_db_row(r) for r in cur.fetchall()]
            except Exception as c_err:
                conn.rollback()
                current_app.logger.warning(f"[ACADEMY] Courses query warning: {c_err}")

            try:
                cur.execute('SELECT COUNT(*) FROM "AcademyEnrollments" WHERE status = \'PASSED\';')
                certified_count = cur.fetchone()[0]
            except Exception as enr_err:
                conn.rollback()
                current_app.logger.warning(f"[ACADEMY] Enrollments count warning: {enr_err}")

            try:
                cur.execute('SELECT COUNT(*) FROM "AcademyTenants" WHERE is_active = TRUE;')
                active_tenants = cur.fetchone()[0]
            except Exception as ten_err:
                conn.rollback()
                current_app.logger.warning(f"[ACADEMY] Tenants count warning: {ten_err}")

            # Fetch active packages for the catalog
            try:
                cur.execute('''
                    SELECT p.package_code, p.title, p.target_role, p.description, p.regulatory_standards, p.price_usd
                    FROM "AcademyPackages" p
                    WHERE p.is_active = TRUE
                    ORDER BY p.id ASC;
                ''')
                packages = [serialize_db_row(r) for r in cur.fetchall()]
            except Exception as pkg_err:
                conn.rollback()
                current_app.logger.warning(f"[ACADEMY] Packages fetch warning: {pkg_err}")
                packages = []
    finally:
        conn.close()

    return render_template(
        'academy_catalog.html',
        courses=courses,
        packages=packages,
        certified_count=certified_count,
        active_tenants=active_tenants
    )


@academy_bp.route('/academy/course/<course_code>', methods=['GET'])
def academy_course_player(course_code):
    """Interactive Module Player and Assessment Engine for technicians & clients."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Fetch Course
            cur.execute('''
                SELECT id, course_code, title, category, regulatory_standard, description, estimated_minutes
                FROM "AcademyCourses"
                WHERE course_code = %s;
            ''', (course_code,))
            course = serialize_db_row(cur.fetchone())
            if not course:
                abort(404, description=f"Course {course_code} not found in SigmaAcademy registry.")

            # 2. Fetch Modules
            cur.execute('''
                SELECT id, module_order, module_code, title, summary, content_html, key_takeaways
                FROM "AcademyCourseModules"
                WHERE course_id = %s
                ORDER BY module_order ASC;
            ''', (course['id'],))
            modules = [serialize_db_row(r) for r in cur.fetchall()]

            # 3. Fetch Quiz (without correct answer key for security)
            cur.execute('''
                SELECT id, question_order, question_text, options
                FROM "AcademyQuizQuestions"
                WHERE course_id = %s
                ORDER BY question_order ASC;
            ''', (course['id'],))
            questions = [serialize_db_row(r) for r in cur.fetchall()]
    finally:
        conn.close()

    return render_template(
        'academy_course.html',
        course=course,
        modules=modules,
        questions=questions,
        prefill_student="",
        prefill_email="",
        prefill_worker_type="W2_EMPLOYEE",
        prefill_tenant_slug="hwb",
        magic_token="",
        assigned_package=""
    )


@academy_bp.route('/academy/learn', methods=['GET'])
def academy_magic_learner():
    """Frictionless smartphone entrypoint for candidates via magic token link."""
    token = (request.args.get('token') or '').strip()
    if not token:
        return redirect('/academy')

    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT 
                    e.id, e.enrollment_uuid, e.magic_token, e.student_name, e.student_email,
                    e.worker_type, e.status, e.assigned_package_code, e.course_id,
                    c.course_code, c.title as course_title, c.regulatory_standard,
                    c.description as course_desc, c.estimated_minutes,
                    t.slug as tenant_slug, t.display_name as tenant_name
                FROM "AcademyEnrollments" e
                JOIN "AcademyCourses" c ON c.id = e.course_id
                JOIN "AcademyTenants" t ON t.id = e.tenant_id
                WHERE e.magic_token = %s;
            ''', (token,))
            enrollment = serialize_db_row(cur.fetchone())

            if not enrollment:
                return redirect('/academy')

            # If already passed, send them straight to their verifiable credential!
            if enrollment.get('status') == 'PASSED':
                return redirect(f"/verify/{enrollment['enrollment_uuid']}")

            # Fetch Modules
            cur.execute('''
                SELECT id, module_order, module_code, title, summary, content_html, key_takeaways
                FROM "AcademyCourseModules"
                WHERE course_id = %s
                ORDER BY module_order ASC;
            ''', (enrollment['course_id'],))
            modules = [serialize_db_row(r) for r in cur.fetchall()]

            # Fetch Quiz
            cur.execute('''
                SELECT id, question_order, question_text, options
                FROM "AcademyQuizQuestions"
                WHERE course_id = %s
                ORDER BY question_order ASC;
            ''', (enrollment['course_id'],))
            questions = [serialize_db_row(r) for r in cur.fetchall()]

    finally:
        conn.close()

    course_obj = {
        'id': enrollment['course_id'],
        'course_code': enrollment['course_code'],
        'title': enrollment['course_title'],
        'regulatory_standard': enrollment['regulatory_standard'],
        'description': enrollment['course_desc'],
        'estimated_minutes': enrollment['estimated_minutes']
    }

    return render_template(
        'academy_course.html',
        course=course_obj,
        modules=modules,
        questions=questions,
        prefill_student=enrollment['student_name'],
        prefill_email=enrollment['student_email'] or '',
        prefill_worker_type=enrollment['worker_type'],
        prefill_tenant_slug=enrollment['tenant_slug'],
        magic_token=token,
        assigned_package=enrollment.get('assigned_package_code') or ''
    )


@academy_bp.route('/verify/<enrollment_uuid>', methods=['GET'])
def public_verify_credential(enrollment_uuid):
    """Public, mobile-optimized QR code verification screen for jobsites & inspectors."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT 
                    e.enrollment_uuid, e.student_name, e.student_email, e.worker_type,
                    e.status, e.quiz_score, e.practical_skills_verified,
                    e.supervisor_evaluator_name, e.supervisor_evaluation_date,
                    e.certified_at, e.expires_at, e.assigned_package_code,
                    c.course_code, c.title as course_title, c.regulatory_standard,
                    t.display_name as tenant_name, t.brand_logo_url
                FROM "AcademyEnrollments" e
                JOIN "AcademyCourses" c ON c.id = e.course_id
                JOIN "AcademyTenants" t ON t.id = e.tenant_id
                WHERE e.enrollment_uuid = %s;
            ''', (enrollment_uuid,))
            row = cur.fetchone()
            if not row:
                return render_template('academy_verify.html', found=False, uuid=enrollment_uuid), 404
            credential = serialize_db_row(row)
    finally:
        conn.close()

    # Determine Active Validity
    now = datetime.datetime.now(datetime.timezone.utc)
    is_valid = False
    if credential.get('status') == 'PASSED':
        expires_at_str = credential.get('expires_at')
        if expires_at_str:
            expires_at = datetime.datetime.fromisoformat(expires_at_str)
            is_valid = (expires_at > now)

    return render_template(
        'academy_verify.html',
        found=True,
        credential=credential,
        is_valid=is_valid,
        uuid=enrollment_uuid
    )


# ==============================================================================
# 2.0 REST API ENDPOINTS
# ==============================================================================

@academy_bp.route('/api/v1/academy/packages', methods=['GET'])
def api_list_packages():
    """Returns all active curriculum bundles with their included courses."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT 
                    p.id, p.package_code, p.title, p.target_role, p.description,
                    p.regulatory_standards, p.price_usd,
                    COALESCE(json_agg(
                        json_build_object(
                            'course_id', c.id,
                            'course_code', c.course_code,
                            'title', c.title,
                            'order', pc.display_order
                        ) ORDER BY pc.display_order
                    ) FILTER (WHERE c.id IS NOT NULL), '[]'::json) as courses
                FROM "AcademyPackages" p
                LEFT JOIN "AcademyPackageCourses" pc ON pc.package_id = p.id
                LEFT JOIN "AcademyCourses" c ON c.id = pc.course_id
                WHERE p.is_active = TRUE
                GROUP BY p.id
                ORDER BY p.id ASC;
            ''')
            packages = [serialize_db_row(r) for r in cur.fetchall()]
        return jsonify({'status': 'success', 'count': len(packages), 'packages': packages}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@academy_bp.route('/api/v1/academy/assign', methods=['POST'])
def api_assign_training():
    """
    Assigns an individual course or pre-configured curriculum package to a candidate.
    Generates an automated magic token and onboarding URL for SMS/Email dispatch.
    """
    data = request.get_json() or {}
    student_name = (data.get('student_name') or '').strip()
    student_email = (data.get('student_email') or '').strip()
    worker_type = data.get('worker_type', 'W2_EMPLOYEE')
    employee_id = data.get('employee_id')
    subcontractor_id = data.get('subcontractor_id')
    assignment_type = data.get('assignment_type', 'PACKAGE')  # 'PACKAGE' or 'COURSE'
    target_code = (data.get('target_code') or 'PKG-CORE-W2').strip()
    tenant_slug = data.get('tenant_slug', 'hwb')
    due_days = int(data.get('due_days', 7))
    assigned_by = data.get('assigned_by', 'CEO Humberto Dominguez')

    if not student_name:
        return jsonify({'status': 'error', 'message': 'Candidate name is required.'}), 400

    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Resolve Tenant
            cur.execute('SELECT id, display_name FROM "AcademyTenants" WHERE slug = %s;', (tenant_slug,))
            t_row = cur.fetchone()
            tenant_id = t_row[0] if t_row else 1

            # Validate optional foreign keys
            if employee_id:
                cur.execute('SELECT id FROM "Employees" WHERE id = %s;', (employee_id,))
                if not cur.fetchone():
                    employee_id = None
            if subcontractor_id:
                cur.execute('SELECT id FROM "SubcontractorPartners" WHERE id = %s;', (subcontractor_id,))
                if not cur.fetchone():
                    subcontractor_id = None

            # 2. Generate Magic Token & Due Date
            magic_token = f"tok_{uuid.uuid4().hex[:16]}"
            due_date = datetime.date.today() + datetime.timedelta(days=due_days)

            assigned_courses = []

            if assignment_type == 'PACKAGE':
                cur.execute('''
                    SELECT c.id, c.course_code, c.title
                    FROM "AcademyPackages" p
                    JOIN "AcademyPackageCourses" pc ON pc.package_id = p.id
                    JOIN "AcademyCourses" c ON c.id = pc.course_id
                    WHERE p.package_code = %s
                    ORDER BY pc.display_order ASC;
                ''', (target_code,))
                course_rows = cur.fetchall()
                if not course_rows:
                    return jsonify({'status': 'error', 'message': f'Package {target_code} has no courses assigned.'}), 404

                for c_id, c_code, c_title in course_rows:
                    enrollment_uuid = f"cert-{uuid.uuid4().hex[:12]}"
                    cur.execute('''
                        INSERT INTO "AcademyEnrollments" (
                            enrollment_uuid, magic_token, tenant_id, course_id, worker_type,
                            employee_id, subcontractor_id, student_name, student_email,
                            assigned_package_code, assigned_by, due_date, status, progress_pct
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ENROLLED', 0)
                        RETURNING id;
                    ''', (
                        enrollment_uuid, magic_token, tenant_id, c_id, worker_type,
                        employee_id if employee_id else None,
                        subcontractor_id if subcontractor_id else None,
                        student_name, student_email,
                        target_code, assigned_by, due_date
                    ))
                    assigned_courses.append({'id': c_id, 'code': c_code, 'title': c_title})

            else:
                # Individual Course
                cur.execute('SELECT id, course_code, title FROM "AcademyCourses" WHERE course_code = %s;', (target_code,))
                c_row = cur.fetchone()
                if not c_row:
                    return jsonify({'status': 'error', 'message': f'Course {target_code} not found.'}), 404
                c_id, c_code, c_title = c_row
                enrollment_uuid = f"cert-{uuid.uuid4().hex[:12]}"
                cur.execute('''
                    INSERT INTO "AcademyEnrollments" (
                        enrollment_uuid, magic_token, tenant_id, course_id, worker_type,
                        employee_id, subcontractor_id, student_name, student_email,
                        assigned_package_code, assigned_by, due_date, status, progress_pct
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, 'ENROLLED', 0)
                    RETURNING id;
                ''', (
                    enrollment_uuid, magic_token, tenant_id, c_id, worker_type,
                    employee_id if employee_id else None,
                    subcontractor_id if subcontractor_id else None,
                    student_name, student_email,
                    assigned_by, due_date
                ))
                assigned_courses.append({'id': c_id, 'code': c_code, 'title': c_title})

            conn.commit()

        magic_url = f"/academy/learn?token={magic_token}"
        full_url = f"https://www.hwbcleaning.com{magic_url}"

        return jsonify({
            'status': 'success',
            'message': f"Successfully assigned {target_code} ({len(assigned_courses)} courses) to {student_name}.",
            'magic_token': magic_token,
            'magic_url': magic_url,
            'full_url': full_url,
            'student_name': student_name,
            'due_date': due_date.isoformat(),
            'target_code': target_code,
            'courses': assigned_courses
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@academy_bp.route('/api/v1/academy/courses', methods=['GET'])
def api_list_courses():
    """Returns JSON list of all available training courses with module counts."""
    category = request.args.get('category')
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            query = '''
                SELECT 
                    c.id, c.course_code, c.title, c.category, c.regulatory_standard,
                    c.description, c.estimated_minutes, c.renewal_months, c.badge_icon,
                    COUNT(DISTINCT m.id) as module_count,
                    COUNT(DISTINCT q.id) as question_count
                FROM "AcademyCourses" c
                LEFT JOIN "AcademyCourseModules" m ON m.course_id = c.id
                LEFT JOIN "AcademyQuizQuestions" q ON q.course_id = c.id
            '''
            params = []
            if category:
                query += ' WHERE c.category = %s'
                params.append(category)
            query += ' GROUP BY c.id ORDER BY c.id ASC;'

            cur.execute(query, tuple(params))
            courses = [serialize_db_row(r) for r in cur.fetchall()]
        return jsonify({'status': 'success', 'count': len(courses), 'courses': courses}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@academy_bp.route('/api/v1/academy/courses/<course_code>', methods=['GET'])
def api_get_course_detail(course_code):
    """Returns full course details and all module contents in order."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, course_code, title, category, regulatory_standard, description, estimated_minutes, renewal_months
                FROM "AcademyCourses"
                WHERE course_code = %s;
            ''', (course_code,))
            course = serialize_db_row(cur.fetchone())
            if not course:
                return jsonify({'status': 'error', 'message': f'Course {course_code} not found'}), 404

            cur.execute('''
                SELECT id, module_order, module_code, title, summary, content_html, key_takeaways
                FROM "AcademyCourseModules"
                WHERE course_id = %s
                ORDER BY module_order ASC;
            ''', (course['id'],))
            modules = [serialize_db_row(r) for r in cur.fetchall()]
            course['modules'] = modules

        return jsonify({'status': 'success', 'course': course}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@academy_bp.route('/api/v1/academy/courses/<course_code>/quiz', methods=['GET'])
def api_get_course_quiz(course_code):
    """Returns sanitized quiz questions without answer keys."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT q.id, q.question_order, q.question_text, q.options
                FROM "AcademyQuizQuestions" q
                JOIN "AcademyCourses" c ON c.id = q.course_id
                WHERE c.course_code = %s
                ORDER BY q.question_order ASC;
            ''', (course_code,))
            questions = [serialize_db_row(r) for r in cur.fetchall()]
        return jsonify({'status': 'success', 'course_code': course_code, 'questions': questions}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@academy_bp.route('/api/v1/academy/courses/<course_code>/submit-quiz', methods=['POST'])
def api_submit_course_quiz(course_code):
    """
    Submits student responses, calculates empirical score,
    and issues/updates an immutable verifiable credential on passing score (>= 80%).
    """
    data = request.get_json() or {}
    student_name = (data.get('student_name') or '').strip()
    student_email = (data.get('student_email') or '').strip()
    worker_type = data.get('worker_type', 'W2_EMPLOYEE')
    employee_id = data.get('employee_id')
    subcontractor_id = data.get('subcontractor_id')
    tenant_slug = data.get('tenant_slug', 'hwb')
    magic_token = (data.get('magic_token') or '').strip()
    submitted_answers = data.get('answers', {})

    if not student_name:
        return jsonify({'status': 'error', 'message': 'Student name is required.'}), 400

    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Verify Course
            cur.execute('SELECT id, title, renewal_months FROM "AcademyCourses" WHERE course_code = %s;', (course_code,))
            c_row = cur.fetchone()
            if not c_row:
                return jsonify({'status': 'error', 'message': 'Invalid course code.'}), 404
            course_id, course_title, renewal_months = c_row

            # 2. Get Tenant
            cur.execute('SELECT id FROM "AcademyTenants" WHERE slug = %s;', (tenant_slug,))
            t_row = cur.fetchone()
            tenant_id = t_row[0] if t_row else 1

            # 3. Fetch Answer Key
            cur.execute('''
                SELECT id, correct_option_id, explanation_text
                FROM "AcademyQuizQuestions"
                WHERE course_id = %s;
            ''', (course_id,))
            questions = cur.fetchall()
            total_questions = len(questions)
            if total_questions == 0:
                return jsonify({'status': 'error', 'message': 'No quiz questions registered for this course.'}), 400

            correct_count = 0
            question_feedback = []
            for q_id, correct_opt, explanation in questions:
                user_ans = str(submitted_answers.get(str(q_id)) or submitted_answers.get(q_id) or '').strip().upper()
                is_correct = (user_ans == correct_opt.upper())
                if is_correct:
                    correct_count += 1
                question_feedback.append({
                    'question_id': q_id,
                    'is_correct': is_correct,
                    'user_answer': user_ans,
                    'correct_answer': correct_opt,
                    'explanation': explanation
                })

            score = int(round((correct_count / total_questions) * 100))
            passed = (score >= 80)
            status_val = 'PASSED' if passed else 'FAILED'

            certified_at = datetime.datetime.now(datetime.timezone.utc) if passed else None
            expires_at = (certified_at + datetime.timedelta(days=renewal_months * 30)) if passed else None

            # 4. Check for Existing Enrollment with Magic Token
            existing_enrollment = None
            if magic_token:
                cur.execute('''
                    SELECT id, enrollment_uuid, quiz_attempts 
                    FROM "AcademyEnrollments" 
                    WHERE magic_token = %s AND course_id = %s;
                ''', (magic_token, course_id))
                existing_enrollment = cur.fetchone()

            if existing_enrollment:
                existing_id, enrollment_uuid, attempts = existing_enrollment
                cur.execute('''
                    UPDATE "AcademyEnrollments" SET
                        status = %s,
                        progress_pct = %s,
                        quiz_score = %s,
                        quiz_attempts = %s,
                        quiz_responses = %s,
                        practical_skills_verified = %s,
                        supervisor_evaluator_name = %s,
                        supervisor_evaluation_date = %s,
                        certified_at = %s,
                        expires_at = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (
                    status_val, 100 if passed else 50, score, (attempts or 0) + 1,
                    json.dumps(submitted_answers),
                    passed,
                    'George (Systems Architect)' if passed else None,
                    datetime.date.today() if passed else None,
                    certified_at, expires_at,
                    existing_id
                ))
            else:
                enrollment_uuid = f"cert-{uuid.uuid4().hex[:12]}"
                cur.execute('''
                    INSERT INTO "AcademyEnrollments" (
                        enrollment_uuid, magic_token, tenant_id, course_id, worker_type,
                        employee_id, subcontractor_id, student_name, student_email,
                        status, progress_pct, quiz_score, quiz_attempts, quiz_responses,
                        practical_skills_verified, supervisor_evaluator_name, supervisor_evaluation_date,
                        certified_at, expires_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s
                    ) RETURNING id;
                ''', (
                    enrollment_uuid, magic_token if magic_token else None, tenant_id, course_id, worker_type,
                    employee_id if employee_id else None,
                    subcontractor_id if subcontractor_id else None,
                    student_name, student_email,
                    status_val, 100 if passed else 50, score, 1,
                    json.dumps(submitted_answers),
                    passed,
                    'George (Systems Architect)' if passed else None,
                    datetime.date.today() if passed else None,
                    certified_at, expires_at
                ))

            conn.commit()

        return jsonify({
            'status': status_val,
            'passed': passed,
            'score': score,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'enrollment_uuid': enrollment_uuid if passed else None,
            'verification_url': f"/verify/{enrollment_uuid}" if passed else None,
            'feedback': question_feedback
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@academy_bp.route('/api/v1/academy/enrollments', methods=['GET'])
def api_list_enrollments():
    """Lists certified roster and progress records for operations tracking."""
    status_filter = request.args.get('status')
    tenant_filter = request.args.get('tenant')
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            query = '''
                SELECT 
                    e.id, e.enrollment_uuid, e.magic_token, e.student_name, e.student_email, e.worker_type,
                    e.status, e.progress_pct, e.quiz_score, e.practical_skills_verified,
                    e.due_date, e.assigned_package_code, e.assigned_by,
                    e.certified_at, e.expires_at,
                    c.course_code, c.title as course_title,
                    t.display_name as tenant_name, t.slug as tenant_slug
                FROM "AcademyEnrollments" e
                JOIN "AcademyCourses" c ON c.id = e.course_id
                JOIN "AcademyTenants" t ON t.id = e.tenant_id
            '''
            clauses = []
            params = []
            if status_filter:
                clauses.append('e.status = %s')
                params.append(status_filter)
            if tenant_filter:
                clauses.append('t.slug = %s')
                params.append(tenant_filter)
            if clauses:
                query += ' WHERE ' + ' AND '.join(clauses)
            query += ' ORDER BY e.id DESC LIMIT 100;'

            cur.execute(query, tuple(params))
            enrollments = [serialize_db_row(r) for r in cur.fetchall()]
        return jsonify({'status': 'success', 'count': len(enrollments), 'enrollments': enrollments}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()
