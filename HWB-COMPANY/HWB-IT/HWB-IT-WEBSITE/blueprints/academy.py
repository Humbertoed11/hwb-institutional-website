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
    try:
        with conn.cursor() as cur:
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

            cur.execute('SELECT COUNT(*) FROM "AcademyEnrollments" WHERE status = \'PASSED\';')
            certified_count = cur.fetchone()[0]

            cur.execute('SELECT COUNT(*) FROM "AcademyTenants" WHERE is_active = TRUE;')
            active_tenants = cur.fetchone()[0]
    finally:
        conn.close()

    return render_template(
        'academy_catalog.html',
        courses=courses,
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
        questions=questions
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
                    e.certified_at, e.expires_at,
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
    and issues an immutable verifiable credential on passing score (>= 80%).
    """
    data = request.get_json() or {}
    student_name = (data.get('student_name') or '').strip()
    student_email = (data.get('student_email') or '').strip()
    worker_type = data.get('worker_type', 'W2_EMPLOYEE')
    employee_id = data.get('employee_id')
    subcontractor_id = data.get('subcontractor_id')
    tenant_slug = data.get('tenant_slug', 'hwb')
    submitted_answers = data.get('answers', {})  # format: {"question_id": "B", ...}

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

            # 4. Generate Verifiable Enrollment Record
            enrollment_uuid = f"cert-{uuid.uuid4().hex[:12]}"
            certified_at = datetime.datetime.now(datetime.timezone.utc) if passed else None
            expires_at = (certified_at + datetime.timedelta(days=renewal_months * 30)) if passed else None

            cur.execute('''
                INSERT INTO "AcademyEnrollments" (
                    enrollment_uuid, tenant_id, course_id, worker_type,
                    employee_id, subcontractor_id, student_name, student_email,
                    status, progress_pct, quiz_score, quiz_attempts, quiz_responses,
                    practical_skills_verified, supervisor_evaluator_name, supervisor_evaluation_date,
                    certified_at, expires_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                ) RETURNING id;
            ''', (
                enrollment_uuid, tenant_id, course_id, worker_type,
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
                    e.id, e.enrollment_uuid, e.student_name, e.student_email, e.worker_type,
                    e.status, e.progress_pct, e.quiz_score, e.practical_skills_verified,
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
