from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from teacher_db import create_connection # Note: importing from the new db file
import mysql.connector
from functools import wraps
import datetime

app = Flask(__name__, template_folder='templates') # Assuming teacher_portal.html is in a 'templates' folder
app.secret_key = 'a_different_teacher_secret_key' # Using a separate secret key for this app

# --- Add this new route for the root URL ---
@app.route('/')
def index():
    """Redirects the base URL to the teacher login page."""
    return redirect(url_for('teacher_login_page'))

# --- Decorator for teacher authentication ---
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'teacher':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('teacher_login_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- Teacher Portal Routes ---

@app.route('/teacher')
def teacher_login_page():
    """Renders the teacher portal login page."""
    return render_template('teacher_portal.html')

@app.route('/teacher/login', methods=['POST'])
def teacher_login_action():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

    conn = create_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection error.'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Teachers WHERE email = %s AND password = %s", (email, password))
        teacher = cursor.fetchone()
        
        if teacher:
            session['user_type'] = 'teacher'
            session['user_id'] = teacher['teacher_id']
            session['user_name'] = teacher['name']
            return jsonify({
                'success': True, 
                'teacher': {'name': teacher['name'], 'id': teacher['teacher_id']}
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials.'}), 401
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f'Database error: {err}'}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/teacher/logout', methods=['POST'])
def teacher_logout():
    session.clear()
    return jsonify({'success': True})


# --- Teacher API Endpoints ---

@app.route('/api/teacher/session')
def teacher_session():
    """Checks if a teacher is logged in to maintain session on frontend."""
    if session.get('user_type') == 'teacher':
        return jsonify({
            'logged_in': True,
            'teacher': { 'id': session.get('user_id'), 'name': session.get('user_name') }
        })
    return jsonify({'logged_in': False})

@app.route('/api/teacher/schedule')
@teacher_required
def get_teacher_schedule():
    teacher_id = session.get('user_id')
    conn = create_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT s.day_of_week, s.start_time, s.end_time, c.class_name, sub.subject_name
            FROM Schedules s
            JOIN Classes c ON s.class_id = c.class_id
            JOIN Subjects sub ON s.subject_id = sub.subject_id
            WHERE s.teacher_id = %s
        """
        cursor.execute(query, (teacher_id,))
        schedule = cursor.fetchall()
        for item in schedule:
            item['start_time'] = str(item['start_time'])
            item['end_time'] = str(item['end_time'])
        return jsonify({'success': True, 'data': schedule})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/teacher/today_classes')
@teacher_required
def get_today_classes():
    teacher_id = session.get('user_id')
    today_name = datetime.datetime.now().strftime('%A')

    conn = create_connection()
    if not conn:
         return jsonify({'success': False, 'message': 'Database connection error'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT s.schedule_id, s.start_time, s.end_time, c.class_name, sub.subject_name
            FROM Schedules s
            JOIN Classes c ON s.class_id = c.class_id
            JOIN Subjects sub ON s.subject_id = sub.subject_id
            WHERE s.teacher_id = %s AND s.day_of_week = %s
            ORDER BY s.start_time
        """
        cursor.execute(query, (teacher_id, today_name))
        classes = cursor.fetchall()
        for item in classes:
            item['start_time'] = str(item['start_time'])
            item['end_time'] = str(item['end_time'])
        return jsonify({'success': True, 'data': classes})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/teacher/all_classes')
@teacher_required
def get_all_teacher_classes():
    teacher_id = session.get('user_id')
    conn = create_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT DISTINCT s.schedule_id, c.class_name, sub.subject_name, s.start_time, s.end_time
            FROM Schedules s
            JOIN Classes c ON s.class_id = c.class_id
            JOIN Subjects sub ON s.subject_id = sub.subject_id
            WHERE s.teacher_id = %s
            ORDER BY c.class_name, sub.subject_name
        """
        cursor.execute(query, (teacher_id,))
        classes = cursor.fetchall()
        for item in classes:
            item['start_time'] = str(item['start_time'])
            item['end_time'] = str(item['end_time'])
        return jsonify({'success': True, 'data': classes})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/teacher/attendance')
@teacher_required
def view_attendance():
    schedule_id = request.args.get('schedule_id')
    date = request.args.get('date')

    if not schedule_id or not date:
        return jsonify({'success': False, 'message': 'Schedule ID and date are required.'}), 400

    conn = create_connection()
    if not conn:
         return jsonify({'success': False, 'message': 'Database connection error'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT st.name as student_name, st.email as student_email, a.status, a.timestamp
            FROM Attendance a
            JOIN Students st ON a.student_id = st.student_id
            WHERE a.schedule_id = %s AND a.attendance_date = %s
        """
        cursor.execute(query, (schedule_id, date))
        records = cursor.fetchall()
        return jsonify({'success': True, 'data': records})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    # Running on port 5001 to avoid conflict with the admin app on port 5000
    app.run(debug=True, port=5001)