# Scholar AI - Machine Learning-Based Student Performance Prediction System

Scholar AI is a complete, real-time web application designed to predict student academic performance and classify students into one of three risk categories: **High**, **Average**, or **At-Risk**. 

Its primary purpose is **early intervention**—allowing teachers to identify at-risk students before examinations and access personalized, rule-based academic support recommendations.

---

## Key Features

1. **Teacher Dashboard**: High-level statistical cards showing cohort counts, risk rate, and key performance averages (attendance, study time, assignments). Displays interactive Chart.js graphs reflecting the current model predictions.
2. **Student Performance Predictor**: An interactive form for real-time inference. Generates classification category, confidence, probability distribution, and student-specific recommendations using a rule-based engine.
3. **Student Registry**: A filterable, searchable, sortable list of the entire student cohort with server-side pagination.
4. **Prediction History Logs**: A persistent log of all manual prediction queries stored in SQLite, allowing teachers to track changes in student categories over time.
5. **Model Analytics & Evaluation**: View model split info (70/15/15), compare the champion **Random Forest** model with baseline classifiers (Logistic Regression, Decision Tree, SVM, KNN), inspect the confusion matrix, and view the global feature importance weights.
6. **Retrain Interface**: Triggers the data extraction, preprocessing, training, and evaluation pipelines to update saved binaries and database tables on the fly.
7. **Secure Teacher Authentication**: Session-based login with hashed passwords.

---

## Technology Stack

- **Frontend**: HTML5, CSS3 (Vanilla CSS, custom dashboard layout), Bootstrap 5, JavaScript (AJAX, Toast alerts), Chart.js
- **Backend**: Python 3.11+, Flask, Jinja2 template engine
- **Machine Learning**: Pandas, NumPy, Scikit-Learn (Random Forest, StandardScaler, OneHotEncoder, ColumnTransformer), Imbalanced-learn (SMOTE class balancing), joblib
- **Database**: SQLite3

---

## Project Structure

```
scholar-ai/
├── app.py                     # Main Flask Application
├── requirements.txt           # Python dependency requirements
├── README.md                  # Documentation
├── .env                       # Active environment configurations
├── .env.example               # Template environment configuration
├── data/
│   ├── generate_data.py       # Script to generate synthetic dataset
│   └── students.csv           # Cohort CSV dataset
├── model/
│   ├── model.pkl              # Saved Random Forest classifier binary
│   ├── preprocessing.pkl      # Saved ColumnTransformer preprocessor binary
│   └── split_info.json        # Metadata about dataset splits
├── database/
│   ├── database.py            # SQLite schema initialization and connection management
│   └── scholar_ai.db          # Active SQLite database file
├── ml/
│   ├── train.py               # ML training and evaluation script
│   ├── preprocess.py          # Data preprocessing pipelines
│   └── evaluate.py            # Model metrics console reporter
├── services/
│   ├── prediction_service.py  # Model inference and feature contribution weights
│   └── recommendation_service.py # Rule-based action recommendations
├── templates/                 # Jinja2 HTML layouts
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── predict.html
│   ├── students.html
│   ├── student_profile.html
│   ├── history.html
│   ├── model.html
│   └── settings.html
├── static/                    # Frontend assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── tests/
    └── test_app.py            # Pytest automated test scripts
```

---

## Installation & Setup (Windows Power Shell)

Follow these exact steps to clone, configure, and launch the application locally on Windows.

### 1. Set up Virtual Environment
Open PowerShell inside the project directory (`C:\Users\Admin\.gemini\antigravity\scratch\scholar-ai`) and run:
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Initialize Environment Config
Create a `.env` file from the example:
```powershell
copy .env.example .env
```
Ensure you have set the secret key and the teacher user login parameters:
- `TEACHER_USERNAME=admin`
- `TEACHER_PASSWORD=admin123`

### 4. Run Model Training & Database Seeding
This will generate the synthetic student dataset of 1,043 records, initialize SQLite tables, train all classifiers, log their evaluation metrics, and populate the cohort database:
```powershell
python ml/train.py
```
To print the model training report in the terminal:
```powershell
python ml/evaluate.py
```

### 5. Run Flask Application
Start the local server:
```powershell
python app.py
```
The application will launch on [http://127.0.0.1:5000/](http://127.0.0.1:5000/). 

Sign in using the default credentials:
- **Username**: `admin`
- **Password**: `admin123`

---

## Automated Unit Testing

Run the automated tests to verify route accessibility, authentication logic, database writes, and predictions:
```powershell
pytest
```

---

## API Documentation

The backend exposes the following REST API endpoints:

- `POST /api/predict`: Runs real-time inference on a student profile. Inserts details into prediction history and updates the cohort.
- `GET /api/metrics`: Retrieves trained model comparison scores, splits count, and confusion matrix.
- `POST /api/retrain`: Triggers retraining for all models and outputs updated metrics and binaries.
- `DELETE /api/predictions`: Permanently deletes all stored prediction history logs.

---

## Vercel Deployment Guide

To deploy this application to Vercel, follow these instructions:

### ⚙️ Prerequisites
1. Install [Node.js](https://nodejs.org/) (which includes `npm`).
2. Install the Vercel CLI globally:
   ```bash
   npm install -g vercel
   ```

### 🚀 Deployment Instructions
1. **Authenticate Vercel CLI**:
   ```bash
   vercel login
   ```
2. **Launch Local Vercel Development Server**:
   Verify everything operates correctly inside the Vercel local emulation server:
   ```bash
   vercel dev
   ```
   The Vercel environment will run locally at **http://localhost:3000/**.
3. **Set Up Vercel Environment Variables**:
   In your Vercel dashboard under **Settings > Environment Variables**, configure:
   * `SECRET_KEY`: A secure random cryptographic key for session hashing.
   * `TEACHER_USERNAME`: Default admin username (e.g. `admin`).
   * `TEACHER_PASSWORD`: Default admin password (e.g. `admin123`).
   * `DATABASE_URL`: *(Optional)* A valid PostgreSQL database URI (e.g. `postgresql://user:pass@host:5432/db`).
   
   > [!NOTE]
   > If `DATABASE_URL` is omitted, the application uses **SQLite in Ephemeral Mode** by copying the template database to `/tmp/scholar_ai.db`. While fully writable, this database resets during serverless function cold starts. For persistent databases, configure `DATABASE_URL`.

4. **Deploy to Production**:
   Deploy the project live to Vercel's edge network:
   ```bash
   vercel --prod
   ```

### 📂 Vercel Deployment Assets
* **[`vercel.json`](file:///C:/Users/Admin/.gemini/antigravity/scratch/scholar-ai/vercel.json)**: Maps routing rewrites and serves `/static/` paths directly via Vercel CDN.
* **[`api/index.py`](file:///C:/Users/Admin/.gemini/antigravity/scratch/scholar-ai/api/index.py)**: Exposes the entrypoint Flask application object as `app` to Vercel's Python serverless runtime.
* **[`requirements.txt`](file:///C:/Users/Admin/.gemini/antigravity/scratch/scholar-ai/requirements.txt)**: Specifies package builds including `psycopg2-binary` for database integration.
