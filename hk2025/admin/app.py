from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from db import create_connection
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key' # Change this to a secure, random key

# --- Authentication ---
@app.route('/', methods=['GET', 'POST'])
def login():
    """Handles admin login."""
    # (Same login logic as before)
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            conn = create_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM Admins WHERE email = %s AND password = %s", (email, password))
                admin = cursor.fetchone()
                
                if admin:
                    session['logged_in'] = True
                    session['email'] = admin['email']
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Invalid Credentials. Please try again.'
                    return render_template('login.html', error=error)
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            error = 'Database error. Please try again later.'
            return render_template('login.html', error=error)
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logs the admin out."""
    session.pop('logged_in', None)
    session.pop('email', None)
    return redirect(url_for('login'))

def admin_required(func):
    """Decorator to ensure a user is logged in as an admin."""
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__ 
    return wrapper

# --- Main Dashboard Route ---
@app.route('/dashboard')
@admin_required
def dashboard():
    """Renders the single-page admin portal."""
    return render_template('admin_portal.html')

# --- API Endpoints for Data Fetching ---
@app.route('/classes')
@admin_required
def get_classes():
    conn = create_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT class_id as id, class_name as name FROM Classes")
        data = cursor.fetchall()
        return jsonify({'success': True, 'data': data})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/subjects')
@admin_required
def get_subjects():
    conn = create_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT subject_id as id, subject_name as name FROM Subjects")
        data = cursor.fetchall()
        return jsonify({'success': True, 'data': data})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/teachers')
@admin_required
def get_teachers():
    conn = create_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT teacher_id as id, name FROM Teachers")
        data = cursor.fetchall()
        return jsonify({'success': True, 'data': data})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/students')
@admin_required
def get_students():
    conn = create_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT student_id as id, name FROM Students")
        data = cursor.fetchall()
        return jsonify({'success': True, 'data': data})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- API Endpoints for Data Submission ---
@app.route('/create_user', methods=['POST'])
@admin_required
def create_user_api():
    data = request.json
    user_type = data['user_type']
    name = data['name']
    email = data['email']
    password = data['password']

    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            if user_type == 'admin':
                cursor.execute("INSERT INTO Admins (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            elif user_type == 'teacher':
                cursor.execute("INSERT INTO Teachers (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            elif user_type == 'student':
                cursor.execute("INSERT INTO Students (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            
            conn.commit()
            return jsonify({'success': True, 'message': f"{user_type.capitalize()} created successfully!"})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f"Error creating user: {str(err)}"})
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/schedule_class', methods=['POST'])
@admin_required
def schedule_class_api():
    data = request.json
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Schedules (class_id, subject_id, teacher_id, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s, %s, %s)",
                           (data['class_id'], data['subject_id'], data['teacher_id'], data['day_of_week'], data['start_time'], data['end_time']))
            conn.commit()
            return jsonify({'success': True, 'message': "Class scheduled successfully!"})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f"Error scheduling class: {str(err)}"})
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/upload_result', methods=['POST'])
@admin_required
def upload_result_api():
    data = request.json
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Results (student_id, subject_id, score, term) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE score = VALUES(score), term = VALUES(term)",
                           (data['student_id'], data['subject_id'], data['score'], data['term']))
            conn.commit()
            return jsonify({'success': True, 'message': "Result uploaded successfully!"})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f"Error uploading result: {str(err)}"})
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/manage_subjects', methods=['POST'])
@admin_required
def manage_subjects_api():
    data = request.json
    action = data['action']
    
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        if action == 'add':
            subject_name = data['subject_name']
            cursor.execute("INSERT INTO Subjects (subject_name) VALUES (%s)", (subject_name,))
            message = f"Subject '{subject_name}' added successfully!"
        elif action == 'remove':
            subject_id = data['subject_id']
            cursor.execute("DELETE FROM Subjects WHERE subject_id = %s", (subject_id,))
            message = "Subject removed successfully!"
            
        conn.commit()
        return jsonify({'success': True, 'message': message})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f"Error managing subjects: {str(err)}"})
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)