import os
import sys
import json
import pytest

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.database import get_db_connection, init_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    
    # Initialize DB for tests
    init_db()
    
    with app.test_client() as client:
        yield client

def test_login_page_renders(client):
    """Test that login page loads successfully."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Scholar AI" in response.data
    assert b"Username" in response.data

def test_register_page_renders(client):
    """Test that registration page loads successfully."""
    response = client.get('/register')
    assert response.status_code == 200
    assert b"Register a new instructor account" in response.data

def test_register_user_success(client):
    """Test registering a new teacher account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM teachers WHERE username = ?", ("newteacher",))
    conn.commit()
    conn.close()

    response = client.post('/register', data={
        'username': 'newteacher',
        'password': 'testpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Account created successfully" in response.data

def test_register_user_duplicate(client):
    """Test that duplicate registrations fail."""
    response = client.post('/register', data={
        'username': 'admin',
        'password': 'somepassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Username already exists" in response.data


def test_dashboard_redirects_unauthenticated(client):
    """Test that unauthenticated requests redirect to login."""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert response.headers['Location'] == '/login'

def test_login_post_invalid(client):
    """Test login with incorrect credentials."""
    response = client.post('/login', data={
        'username': 'wrongteacher',
        'password': 'badpassword'
    }, follow_redirects=True)
    assert b"Invalid username or password" in response.data

def test_login_post_success(client):
    """Test login with correct credentials."""
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)
    assert b"Class Performance Dashboard" in response.data

def test_dashboard_authenticated(client):
    """Test dashboard access with a mocked session."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b"Class Performance Dashboard" in response.data

def test_api_predict_invalid_input(client):
    """Test prediction API with missing parameter."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    # Missing attendance rate
    invalid_payload = {
        "Student_ID": "S-TEST",
        "Study_Hours": 10.0,
        "Assignment_Completion": 80.0,
        "Previous_Grade": 75.0,
        "Class_Participation": 70.0,
        "Family_Support": "Medium",
        "Parental_Education": "Bachelor",
        "Internet_Access": "Yes",
        "Extra_Activities": "No"
    }
    
    response = client.post('/api/predict', 
                           data=json.dumps(invalid_payload),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "Missing required parameter" in data["message"]

def test_api_predict_success(client):
    """Test prediction API with valid parameters."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    valid_payload = {
        "Student_ID": "S-TEST-99",
        "Attendance": 95.0,
        "Study_Hours": 15.0,
        "Assignment_Completion": 90.0,
        "Previous_Grade": 85.0,
        "Class_Participation": 80.0,
        "Family_Support": "High",
        "Parental_Education": "PhD",
        "Internet_Access": "Yes",
        "Extra_Activities": "Yes"
    }
    
    response = client.post('/api/predict', 
                           data=json.dumps(valid_payload),
                           content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "prediction" in data["data"]
    assert "confidence" in data["data"]
    assert "probabilities" in data["data"]
    assert "recommendations" in data["data"]

def test_student_profile_not_found(client):
    """Test searching for a non-existent student profile."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    response = client.get('/student/S-NON-EXISTENT', follow_redirects=True)
    assert b"does not exist in the cohort" in response.data

def test_database_direct_insertion():
    """Test database helper layer connection and table insertions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert dummy prediction row
    cursor.execute(
        """
        INSERT INTO predictions (
            student_id, attendance, study_hours, assignment_percentage,
            previous_grade, class_participation, family_support,
            parental_education, internet_access, extra_activities,
            prediction, confidence, prob_high, prob_average, prob_at_risk
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("S-DB-TEST", 90, 10, 80, 70, 60, "Medium", "Bachelor", "Yes", "No", "Average", 0.8, 0.1, 0.8, 0.1)
    )
    conn.commit()
    
    # Retrieve row
    cursor.execute("SELECT * FROM predictions WHERE student_id = ?", ("S-DB-TEST",))
    row = cursor.fetchone()
    assert row is not None
    assert row["prediction"] == "Average"
    assert row["confidence"] == 0.8
    
    # Clean up dummy row
    cursor.execute("DELETE FROM predictions WHERE student_id = ?", ("S-DB-TEST",))
    conn.commit()
    conn.close()

def test_api_correlation(client):
    """Test Pearson correlation API endpoint."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    response = client.get('/api/correlation')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "features" in data
    assert "matrix" in data
    assert len(data["matrix"]) == len(data["features"])

def test_api_notifications(client):
    """Test notifications API retrieval and read updates."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    # GET list
    response = client.get('/api/notifications')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "notifications" in data
    
    # POST read
    payload = {"all": True}
    response_read = client.post('/api/notifications/read',
                                data=json.dumps(payload),
                                content_type='application/json')
    assert response_read.status_code == 200
    assert json.loads(response_read.data)["success"] is True

def test_api_interventions(client):
    """Test creating and updating interventions."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    payload = {
        "student_id": "S-001",
        "category": "Mentoring",
        "notes": "Testing notes",
        "status": "Pending"
    }
    
    # Create
    response = client.post('/api/interventions',
                           data=json.dumps(payload),
                           content_type='application/json')
    assert response.status_code == 200
    assert json.loads(response.data)["success"] is True
    
    # GET list
    response_list = client.get('/api/interventions')
    assert response_list.status_code == 200
    list_data = json.loads(response_list.data)
    assert list_data["success"] is True
    assert len(list_data["interventions"]) > 0
    
    # Update status
    intervention_id = list_data["interventions"][0]["id"]
    update_payload = {
        "id": intervention_id,
        "student_id": "S-001",
        "notes": "Updated testing notes",
        "status": "In Progress"
    }
    response_update = client.post('/api/interventions',
                                  data=json.dumps(update_payload),
                                  content_type='application/json')
    assert response_update.status_code == 200
    assert json.loads(response_update.data)["success"] is True

def test_dataset_center_renders(client):
    """Test data center page renders successfully."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    response = client.get('/dataset')
    assert response.status_code == 200
    assert b"Data Center" in response.data

def test_download_sample_dataset(client):
    """Test sample dataset CSV downloader."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    response = client.get('/api/samples/download/high_achievers.csv')
    assert response.status_code == 200
    assert b"Student_ID" in response.data

def test_upload_dataset_success(client):
    """Test batch CSV dataset upload processing."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['teacher_id'] = 1
        
    csv_data = (
        "Student_ID,Attendance,Study_Hours,Assignment_Completion,Previous_Grade,Class_Participation,Family_Support,Parental_Education,Internet_Access,Extra_Activities\n"
        "S-UPLOAD-TEST,95.0,15.0,90.0,85.0,80.0,High,Bachelor,Yes,Yes\n"
    )
    
    from io import BytesIO
    response = client.post('/api/dataset/upload',
                           data={'file': (BytesIO(csv_data.encode('utf-8')), 'test_batch.csv')},
                           content_type='multipart/form-data')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["processed"] == 1


