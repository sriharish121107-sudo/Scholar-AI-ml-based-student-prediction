import os
import sys
import json
import sqlite3
import csv
import pandas as pd
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "scholar_ai_super_secret_key_987!")

# Set path configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_db_connection, init_db, DB_PATH
from services.prediction_service import PredictionService
from services.recommendation_service import RecommendationService

prediction_service = PredictionService()

# Ensure database and models exist on startup
def run_initial_training():
    model_path = os.path.join("model", "model.pkl")
    if not os.path.exists(model_path) or not os.path.exists(DB_PATH):
        print("Initial setup: Creating database and training models. Please wait...")
        init_db()
        from ml.train import train_and_evaluate_models
        train_and_evaluate_models()
        print("Initial setup completed.")

# Check for session login before serving dashboard pages
@app.before_request
def check_login():
    # Exclude login, register, static files, and check session
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint not in allowed_routes and 'logged_in' not in session:
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and Password are required.', 'error')
            return render_template('register.html')
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM teachers WHERE username = ?", (username,))
        if cursor.fetchone():
            flash('Username already exists. Please choose another.', 'error')
            conn.close()
            return render_template('register.html')
            
        # Create user
        hashed = generate_password_hash(password)
        try:
            cursor.execute("INSERT INTO teachers (username, password_hash) VALUES (?, ?)", (username, hashed))
            conn.commit()
            flash('Account created successfully! Please sign in.', 'success')
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'error')
            conn.close()
            
    return render_template('register.html')

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teachers WHERE username = ?", (username,))
        teacher = cursor.fetchone()
        conn.close()
        
        if teacher and check_password_hash(teacher['password_hash'], password):
            session['logged_in'] = True
            session['username'] = teacher['username']
            session['teacher_id'] = teacher['id']
            flash('Successfully signed in.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total Student Counts
    cursor.execute("SELECT COUNT(*) as cnt FROM students")
    total_students = cursor.fetchone()['cnt']
    
    if total_students == 0:
        # Fallback empty metrics
        stats = {
            "total_students": 0, "high_count": 0, "average_count": 0, "risk_count": 0,
            "risk_percent": 0.0, "avg_attendance": 0.0, "avg_study_hours": 0.0, "avg_assignment_completion": 0.0
        }
        importances = []
    else:
        cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE predicted_category = 'High'")
        high_count = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE predicted_category = 'Average'")
        average_count = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE predicted_category = 'At-Risk'")
        risk_count = cursor.fetchone()['cnt']
        
        risk_percent = (risk_count / total_students * 100) if total_students > 0 else 0
        
        # 2. General Averages
        cursor.execute("SELECT AVG(attendance) as att, AVG(study_hours) as sh, AVG(assignment_completion) as ac FROM students")
        avg_row = cursor.fetchone()
        
        # 3. Categorical Averages for comparative charts
        cursor.execute("SELECT AVG(attendance) as att, AVG(study_hours) as sh, AVG(assignment_completion) as ac FROM students WHERE predicted_category = 'High'")
        high_avg = cursor.fetchone()
        cursor.execute("SELECT AVG(attendance) as att, AVG(study_hours) as sh, AVG(assignment_completion) as ac FROM students WHERE predicted_category = 'Average'")
        avg_avg = cursor.fetchone()
        cursor.execute("SELECT AVG(attendance) as att, AVG(study_hours) as sh, AVG(assignment_completion) as ac FROM students WHERE predicted_category = 'At-Risk'")
        risk_avg = cursor.fetchone()
        
        stats = {
            "total_students": total_students,
            "high_count": high_count,
            "average_count": average_count,
            "risk_count": risk_count,
            "risk_percent": risk_percent,
            "avg_attendance": avg_row['att'] or 0,
            "avg_study_hours": avg_row['sh'] or 0,
            "avg_assignment_completion": avg_row['ac'] or 0,
            
            # Subgroup metrics for charts
            "high_avg_attendance": high_avg['att'] or 0,
            "high_avg_study_hours": high_avg['sh'] or 0,
            "high_avg_assignment": high_avg['ac'] or 0,
            
            "average_avg_attendance": avg_avg['att'] or 0,
            "average_avg_study_hours": avg_avg['sh'] or 0,
            "average_avg_assignment": avg_avg['ac'] or 0,
            
            "risk_avg_attendance": risk_avg['att'] or 0,
            "risk_avg_study_hours": risk_avg['sh'] or 0,
            "risk_avg_assignment": risk_avg['ac'] or 0,
        }
        
        try:
            importances = prediction_service.get_model_features()
        except Exception as e:
            print("Feature importances failed to load:", e)
            importances = []
            
    conn.close()
    return render_template('dashboard.html', stats=stats, importances=importances)

@app.route('/predict')
def predict():
    return render_template('predict.html')

@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON request payload."}), 400
        
    # Input validation
    required_fields = ["Student_ID", "Attendance", "Study_Hours", "Assignment_Completion", 
                       "Previous_Grade", "Class_Participation", "Extra_Activities"]
                       
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Missing required parameter '{field}'."}), 400
            
    # Perform prediction
    try:
        inputs = {
            "Attendance": float(data["Attendance"]),
            "Study_Hours": float(data["Study_Hours"]),
            "Assignment_Completion": float(data["Assignment_Completion"]),
            "Previous_Grade": float(data["Previous_Grade"]),
            "Class_Participation": float(data["Class_Participation"]),
            "Family_Support": data.get("Family_Support", "Medium"),
            "Parental_Education": data.get("Parental_Education", "Bachelor"),
            "Internet_Access": data.get("Internet_Access", "Yes"),
            "Extra_Activities": data["Extra_Activities"]
        }
        
        pred_res = prediction_service.predict(inputs)
        
        # Format response
        result_label = pred_res["prediction"]
        confidence_val = float(pred_res["confidence"])
        prob_high = float(pred_res["probabilities"]["High"])
        prob_average = float(pred_res["probabilities"]["Average"])
        prob_risk = float(pred_res["probabilities"]["At-Risk"])
        
        # Recommendations
        recs = RecommendationService.get_recommendations(inputs, result_label, confidence_val)
        
        # Write to Database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Update students table
        cursor.execute(
            """
            INSERT OR REPLACE INTO students (
                student_id, attendance, study_hours, assignment_completion,
                previous_grade, class_participation, family_support,
                parental_education, internet_access, extra_activities,
                predicted_category, confidence, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                data["Student_ID"], inputs["Attendance"], inputs["Study_Hours"], inputs["Assignment_Completion"],
                inputs["Previous_Grade"], inputs["Class_Participation"], inputs["Family_Support"],
                inputs["Parental_Education"], inputs["Internet_Access"], inputs["Extra_Activities"],
                result_label, confidence_val
            )
        )
        
        # 2. Append to predictions history table
        teacher_id = session.get('teacher_id')
        cursor.execute(
            """
            INSERT INTO predictions (
                teacher_id, student_id, attendance, study_hours, assignment_percentage,
                previous_grade, class_participation, family_support,
                parental_education, internet_access, extra_activities,
                prediction, confidence, prob_high, prob_average, prob_at_risk, prediction_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                teacher_id, data["Student_ID"], inputs["Attendance"], inputs["Study_Hours"], inputs["Assignment_Completion"],
                inputs["Previous_Grade"], inputs["Class_Participation"], inputs["Family_Support"],
                inputs["Parental_Education"], inputs["Internet_Access"], inputs["Extra_Activities"],
                result_label, confidence_val, prob_high, prob_average, prob_risk
            )
        )
        
        # 3. Generate alert if student is at risk
        if result_label == "At-Risk":
            cursor.execute(
                "INSERT INTO notifications (message, type) VALUES (?, 'danger')",
                (f"🔴 ALERT: Student {data['Student_ID']} predicted as At-Risk ({confidence_val * 100:.1f}% confidence).",)
            )
            
        conn.commit()
        conn.close()
        
        response_payload = {
            "student_id": data["Student_ID"],
            "prediction": result_label,
            "confidence": confidence_val,
            "probabilities": pred_res["probabilities"],
            "recommendations": recs,
            "performance_factors": pred_res["performance_factors"]
        }
        return jsonify({"success": True, "data": response_payload})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Prediction model execution error: {str(e)}"}), 500

@app.route('/students')
def students():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    sort_by = request.args.get('sort', 'student_id').strip()
    page = int(request.args.get('page', 1))
    per_page = 20
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Base query construction
    query = "SELECT * FROM students WHERE 1=1"
    params = []
    
    if search:
        query += " AND student_id LIKE ?"
        params.append(f"%{search}%")
    if category:
        query += " AND predicted_category = ?"
        params.append(category)
        
    # Apply Sorting
    allowed_sorts = ["student_id", "attendance", "study_hours", "assignment_completion", "previous_grade", "confidence"]
    if sort_by not in allowed_sorts:
        sort_by = "student_id"
    
    # Use DESC order for performance numeric values so high values display first
    order_direction = "DESC" if sort_by in ["attendance", "study_hours", "assignment_completion", "previous_grade", "confidence"] else "ASC"
    query += f" ORDER BY {sort_by} {order_direction}"
    
    # Calculate totals for pagination
    cursor.execute(f"SELECT COUNT(*) as count FROM ({query})", params)
    total_records = cursor.fetchone()['count']
    total_pages = (total_records + per_page - 1) // per_page
    
    # Apply pagination bounds
    offset = (page - 1) * per_page
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    student_rows = cursor.fetchall()
    conn.close()
    
    return render_template(
        'students.html',
        students=student_rows,
        search_query=search,
        selected_category=category,
        sort_by=sort_by,
        current_page=page,
        total_pages=total_pages,
        total_records=total_records
    )

@app.route('/student/<student_id>')
def student_profile(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch latest profile
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        flash(f"Student ID '{student_id}' does not exist in the cohort.", "error")
        return redirect(url_for('students'))
        
    # Fetch historical log entries
    cursor.execute(
        """
        SELECT p.*, t.username as teacher_name 
        FROM predictions p 
        LEFT JOIN teachers t ON p.teacher_id = t.id 
        WHERE p.student_id = ? 
        ORDER BY p.prediction_date DESC
        """, 
        (student_id,)
    )
    history_rows = cursor.fetchall()
    conn.close()
    
    # Compute current recommendations
    inputs = {
        "Attendance": student["attendance"],
        "Study_Hours": student["study_hours"],
        "Assignment_Completion": student["assignment_completion"],
        "Previous_Grade": student["previous_grade"],
        "Class_Participation": student["class_participation"]
    }
    recs = RecommendationService.get_recommendations(inputs, student["predicted_category"], student["confidence"])
    
    return render_template(
        'student_profile.html',
        student=student,
        history=history_rows,
        recommendations=recs
    )

@app.route('/history')
def history():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 20
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT p.*, t.username as teacher_name 
        FROM predictions p 
        LEFT JOIN teachers t ON p.teacher_id = t.id 
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND p.student_id LIKE ?"
        params.append(f"%{search}%")
    if category:
        query += " AND p.prediction = ?"
        params.append(category)
        
    query += " ORDER BY p.prediction_date DESC"
    
    # Calculate pagination totals
    cursor.execute(f"SELECT COUNT(*) as count FROM ({query})", params)
    total_records = cursor.fetchone()['count']
    total_pages = (total_records + per_page - 1) // per_page
    
    # Pagination
    offset = (page - 1) * per_page
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    history_rows = cursor.fetchall()
    conn.close()
    
    return render_template(
        'history.html',
        history=history_rows,
        search_query=search,
        selected_category=category,
        current_page=page,
        total_pages=total_pages,
        total_records=total_records
    )

@app.route('/model')
def model():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM model_metrics ORDER BY accuracy DESC")
    metrics_rows = cursor.fetchall()
    conn.close()
    
    try:
        importances = prediction_service.get_model_features()
    except Exception:
        importances = []
        
    return render_template('model.html', metrics=metrics_rows, importances=importances)

@app.route('/api/metrics')
def api_metrics():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_metrics")
        rows = cursor.fetchall()
        conn.close()
        
        metrics_list = []
        for r in rows:
            metrics_list.append({
                "model_name": r["model_name"],
                "accuracy": r["accuracy"],
                "precision": r["precision"],
                "recall": r["recall"],
                "f1_score": r["f1_score"],
                "cv_score": r["cv_score"],
                "confusion_matrix": json.loads(r["confusion_matrix"]) if r["confusion_matrix"] else [],
                "last_trained": r["last_trained"]
            })
            
        # Load split info
        split_path = os.path.join("model", "split_info.json")
        split_info = {}
        if os.path.exists(split_path):
            with open(split_path, "r") as f:
                split_info = json.load(f)
                
        return jsonify({"success": True, "metrics": metrics_list, "split_info": split_info})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/retrain', methods=['POST'])
def api_retrain():
    try:
        from ml.train import train_and_evaluate_models
        train_and_evaluate_models()
        return jsonify({"success": True, "message": "Models successfully retrained."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Retraining failed: {str(e)}"}), 500

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            current_pass = request.form.get('current_password')
            new_pass = request.form.get('new_password')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM teachers WHERE id = ?", (session['teacher_id'],))
            teacher = cursor.fetchone()
            
            if teacher and check_password_hash(teacher['password_hash'], current_pass):
                hashed = generate_password_hash(new_pass)
                cursor.execute("UPDATE teachers SET password_hash = ? WHERE id = ?", (hashed, session['teacher_id']))
                conn.commit()
                flash('Password updated successfully.', 'success')
            else:
                flash('Incorrect current password.', 'error')
            conn.close()
            
    return render_template('settings.html')

@app.route('/api/predictions', methods=['DELETE'])
def api_clear_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM predictions")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Prediction history logs cleared."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/interventions')
def interventions():
    return render_template('interventions.html')

@app.route('/api/interventions', methods=['GET', 'POST'])
def api_interventions():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'GET':
        cursor.execute("""
            SELECT i.*, s.predicted_category 
            FROM interventions i
            LEFT JOIN students s ON i.student_id = s.student_id
            ORDER BY i.created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "student_id": r["student_id"],
                "category": r["category"],
                "notes": r["notes"],
                "status": r["status"],
                "follow_up_date": r["follow_up_date"],
                "created_at": r["created_at"],
                "predicted_category": r["predicted_category"]
            })
        return jsonify({"success": True, "interventions": results})
        
    data = request.json
    if not data:
        conn.close()
        return jsonify({"success": False, "message": "Invalid payload."}), 400
        
    intervention_id = data.get("id")
    if intervention_id:
        status = data.get("status", "Pending")
        notes = data.get("notes", "")
        cursor.execute(
            "UPDATE interventions SET status = ?, notes = ? WHERE id = ?",
            (status, notes, intervention_id)
        )
        conn.commit()
        
        cursor.execute(
            "INSERT INTO notifications (message, type) VALUES (?, 'success')",
            (f"Intervention status updated for student {data.get('student_id')}.",)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Intervention updated successfully."})
        
    student_id = data.get("student_id")
    category = data.get("category")
    notes = data.get("notes", "")
    status = data.get("status", "Pending")
    follow_up_date = data.get("follow_up_date", "")
    
    if not student_id or not category:
        conn.close()
        return jsonify({"success": False, "message": "Student ID and Category are required."}), 400
        
    cursor.execute(
        """
        INSERT INTO interventions (student_id, category, notes, status, follow_up_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (student_id, category, notes, status, follow_up_date)
    )
    conn.commit()
    
    cursor.execute(
        "INSERT INTO notifications (message, type) VALUES (?, 'info')",
        (f"New intervention plan logged for student {student_id}.",)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Intervention logged successfully."})

@app.route('/api/correlation')
def api_correlation():
    try:
        csv_path = os.path.join("data", "students.csv")
        if not os.path.exists(csv_path):
            return jsonify({"success": False, "message": "Dataset CSV not found."}), 404
            
        df = pd.read_csv(csv_path)
        cat_map = {"High": 3, "Average": 2, "At-Risk": 1}
        df["Performance"] = df["Performance_Category"].map(cat_map)
        
        features = [
            "Attendance", 
            "Study_Hours", 
            "Assignment_Completion", 
            "Previous_Grade", 
            "Class_Participation",
            "Performance"
        ]
        
        corr_matrix = df[features].corr().values.tolist()
        return jsonify({"success": True, "features": features, "matrix": corr_matrix})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/notifications', methods=['GET'])
def api_get_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 8")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "message": r["message"],
            "type": r["type"],
            "is_read": bool(r["is_read"]),
            "created_at": r["created_at"]
        })
    return jsonify({"success": True, "notifications": results})

@app.route('/api/notifications/read', methods=['POST'])
def api_mark_notifications_read():
    data = request.json or {}
    notif_id = data.get("id")
    mark_all = data.get("all", False)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if mark_all:
        cursor.execute("UPDATE notifications SET is_read = 1")
    elif notif_id:
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
        
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Notification updated."})

@app.route('/student/<student_id>/export')
def export_student_report(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return "Student not found", 404
        
    cursor.execute("SELECT p.*, t.username as teacher_name FROM predictions p LEFT JOIN teachers t ON p.teacher_id = t.id WHERE p.student_id = ? ORDER BY p.prediction_date DESC", (student_id,))
    history = cursor.fetchall()
    
    cursor.execute("SELECT * FROM interventions WHERE student_id = ? ORDER BY created_at DESC", (student_id,))
    interventions = cursor.fetchall()
    conn.close()
    
    inputs = {
        "Attendance": student["attendance"],
        "Study_Hours": student["study_hours"],
        "Assignment_Completion": student["assignment_completion"],
        "Previous_Grade": student["previous_grade"],
        "Class_Participation": student["class_participation"]
    }
    recs = RecommendationService.get_recommendations(inputs, student["predicted_category"], student["confidence"])
    
    return render_template(
        'student_report.html',
        student=student,
        history=history,
        interventions=interventions,
        recommendations=recs
    )

@app.route('/students/export')
def export_students_csv():
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM students WHERE 1=1"
    params = []
    
    if search:
        query += " AND student_id LIKE ?"
        params.append(f"%{search}%")
    if category:
        query += " AND predicted_category = ?"
        params.append(category)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    si = StringIO()
    cw = csv.writer(si)
    
    cw.writerow([
        "Student ID", "Attendance %", "Study Hours / Wk", "Assignment Completion %", 
        "Previous Grade %", "Class Participation", "Family Support", 
        "Parental Education", "Internet Access", "Extra Activities", "Prediction", "Confidence"
    ])
    
    for r in rows:
        cw.writerow([
            r["student_id"], r["attendance"], r["study_hours"], r["assignment_completion"],
            r["previous_grade"], r["class_participation"], r["family_support"],
            r["parental_education"], r["internet_access"], r["extra_activities"],
            r["predicted_category"], r["confidence"]
        ])
        
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=scholar_ai_student_cohort.csv"}
    )

@app.route('/dataset')
def dataset_center():
    return render_template('dataset.html')

@app.route('/api/samples/download/<filename>')
def download_sample_dataset(filename):
    samples_dir = os.path.join(app.root_path, "data", "samples")
    return send_from_directory(samples_dir, filename, as_attachment=True)

@app.route('/api/dataset/upload', methods=['POST'])
def api_upload_dataset():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400
        
    try:
        df = pd.read_csv(file)
        
        required_cols = {
            "student_id": "Student_ID",
            "attendance": "Attendance",
            "study_hours": "Study_Hours",
            "assignment_completion": "Assignment_Completion",
            "previous_grade": "Previous_Grade",
            "class_participation": "Class_Participation",
            "family_support": "Family_Support",
            "parental_education": "Parental_Education",
            "internet_access": "Internet_Access",
            "extra_activities": "Extra_Activities"
        }
        
        # Lowercase headers to match keys flexibly
        df.columns = [c.strip().lower() for c in df.columns]
        
        missing = []
        for k in required_cols.keys():
            if k not in df.columns:
                missing.append(required_cols[k])
                
        if missing:
            return jsonify({"success": False, "message": f"Missing columns in CSV: {', '.join(missing)}"}), 400
            
        processed_count = 0
        at_risk_count = 0
        stable_count = 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        teacher_id = session.get('teacher_id')
        
        for _, row in df.iterrows():
            inputs = {
                "Attendance": float(row["attendance"]),
                "Study_Hours": float(row["study_hours"]),
                "Assignment_Completion": float(row["assignment_completion"]),
                "Previous_Grade": float(row["previous_grade"]),
                "Class_Participation": float(row["class_participation"]),
                "Family_Support": str(row["family_support"]),
                "Parental_Education": str(row["parental_education"]),
                "Internet_Access": str(row["internet_access"]),
                "Extra_Activities": str(row["extra_activities"])
            }
            
            student_id = str(row["student_id"])
            
            pred_res = prediction_service.predict(inputs)
            result_label = pred_res["prediction"]
            confidence_val = pred_res["confidence"]
            
            prob_high = pred_res["probabilities"]["High"]
            prob_average = pred_res["probabilities"]["Average"]
            prob_risk = pred_res["probabilities"]["At-Risk"]
            
            cursor.execute(
                """
                INSERT INTO students (
                    student_id, attendance, study_hours, assignment_completion,
                    previous_grade, class_participation, family_support,
                    parental_education, internet_access, extra_activities,
                    predicted_category, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    attendance = excluded.attendance,
                    study_hours = excluded.study_hours,
                    assignment_completion = excluded.assignment_completion,
                    previous_grade = excluded.previous_grade,
                    class_participation = excluded.class_participation,
                    family_support = excluded.family_support,
                    parental_education = excluded.parental_education,
                    internet_access = excluded.internet_access,
                    extra_activities = excluded.extra_activities,
                    predicted_category = excluded.predicted_category,
                    confidence = excluded.confidence
                """,
                (
                    student_id, inputs["Attendance"], inputs["Study_Hours"], inputs["Assignment_Completion"],
                    inputs["Previous_Grade"], inputs["Class_Participation"], inputs["Family_Support"],
                    inputs["Parental_Education"], inputs["Internet_Access"], inputs["Extra_Activities"],
                    result_label, confidence_val
                )
            )
            
            cursor.execute(
                """
                INSERT INTO predictions (
                    teacher_id, student_id, attendance, study_hours, assignment_percentage,
                    previous_grade, class_participation, family_support,
                    parental_education, internet_access, extra_activities,
                    prediction, confidence, prob_high, prob_average, prob_at_risk, prediction_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    teacher_id, student_id, inputs["Attendance"], inputs["Study_Hours"], inputs["Assignment_Completion"],
                    inputs["Previous_Grade"], inputs["Class_Participation"], inputs["Family_Support"],
                    inputs["Parental_Education"], inputs["Internet_Access"], inputs["Extra_Activities"],
                    result_label, confidence_val, prob_high, prob_average, prob_risk
                )
            )
            
            processed_count += 1
            if result_label == "At-Risk":
                at_risk_count += 1
                cursor.execute(
                    "INSERT INTO notifications (message, type) VALUES (?, 'danger')",
                    (f"🔴 ALERT: Student {student_id} classified as At-Risk ({confidence_val * 100:.1f}% confidence).",)
                )
            else:
                stable_count += 1
                
        cursor.execute(
            "INSERT INTO notifications (message, type) VALUES (?, 'success')",
            (f"Batch dataset uploaded: {processed_count} students processed successfully.",)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "processed": processed_count,
            "at_risk": at_risk_count,
            "stable": stable_count
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Processing error: {str(e)}"}), 500

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.context_processor
def inject_db_status():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        status = "postgres"
    elif os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        status = "ephemeral"
    else:
        status = "local"
    return dict(db_status=status)

if __name__ == '__main__':
    # Perform initial setup / check
    run_initial_training()
    
    app.run(host='127.0.0.1', port=5000, debug=True)
