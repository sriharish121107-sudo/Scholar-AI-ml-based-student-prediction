import os
import sys
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.preprocess import StudentDataPreprocessor, ALL_FEATURES
from database.database import get_db_connection, init_db

# Try to import SMOTE from imblearn. If not installed yet, we'll handle it
try:
    from imblearn.over_sampling import SMOTE
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "students.csv")
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model")

def load_or_generate_dataset():
    if not os.path.exists(DATA_PATH):
        print("Dataset not found. Generating synthetic dataset...")
        from data.generate_data import generate_student_dataset
        generate_student_dataset(DATA_PATH)
    return pd.read_csv(DATA_PATH)

def clean_data(df):
    # Remove duplicates
    initial_rows = len(df)
    df = df.drop_duplicates()
    diff = initial_rows - len(df)
    if diff > 0:
        print(f"Removed {diff} duplicate rows.")
        
    # Check for missing values in target
    df = df.dropna(subset=["Performance_Category"])
    
    # Outlier detection and handling using IQR for numerical columns
    numerical_cols = ["Attendance", "Study_Hours", "Assignment_Completion", "Previous_Grade", "Class_Participation"]
    for col in numerical_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Clip outliers to lower and upper bounds instead of dropping, to keep records
        outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
        num_outliers = outliers.sum()
        if num_outliers > 0:
            print(f"Clipped {num_outliers} outliers in column '{col}' to range [{lower_bound:.1f}, {upper_bound:.1f}]")
            df[col] = np.clip(df[col], lower_bound, upper_bound)
            
    return df

def train_and_evaluate_models():
    # 1. Load and clean data
    df = load_or_generate_dataset()
    df = clean_data(df)
    
    # 2. Separate features and target
    X = df[ALL_FEATURES]
    y = df["Performance_Category"]
    
    # 3. Train/Validation/Test Split (70/15/15)
    # First split 85% train-val and 15% test
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    # Then split train-val into 70% train and 15% val (relative to original 100%)
    # 15% / 85% = 0.17647
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=(0.15 / 0.85), random_state=42, stratify=y_train_val
    )
    
    print(f"Dataset split sizes - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # 4. Preprocessing Pipeline
    preprocessor = StudentDataPreprocessor()
    X_train_proc = preprocessor.fit_transform(X_train)
    X_val_proc = preprocessor.transform(X_val)
    X_test_proc = preprocessor.transform(X_test)
    
    # 5. Apply SMOTE to training data if classes are imbalanced and SMOTE is available
    if SMOTE_AVAILABLE:
        print("Applying SMOTE to balance class distribution in training data...")
        smote = SMOTE(random_state=42)
        X_train_res, y_train_res = smote.fit_resample(X_train_proc, y_train)
    else:
        print("SMOTE is not available (install imbalanced-learn). Training on raw split.")
        X_train_res, y_train_res = X_train_proc, y_train
        
    # 6. Initialize models
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "KNN": KNeighborsClassifier(n_neighbors=5),
        "Decision Tree": DecisionTreeClassifier(random_state=42, max_depth=6),
        "SVM": SVC(probability=True, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42, max_depth=8)
    }
    
    # 7. Evaluate each model and store metrics
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Initialize DB tables
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear previous metrics
    cursor.execute("DELETE FROM model_metrics")
    
    champion_name = "Random Forest"
    champion_model = None
    
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train_res, y_train_res)
        
        # Predict on Test set
        y_pred = model.predict(X_test_proc)
        
        # Calculate metrics
        acc = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted")
        
        # Calculate Cross Validation score for Random Forest using k=5
        cv_score = 0.0
        if name == champion_name:
            champion_model = model
            # Fit CV on combined train_val to use more data
            X_cv = preprocessor.transform(X_train_val)
            scores = cross_val_score(model, X_cv, y_train_val, cv=5)
            cv_score = float(scores.mean())
            print(f"Random Forest 5-Fold CV Score: {cv_score:.4f}")
            
            # Save confusion matrix for champion model
            cm = confusion_matrix(y_test, y_pred, labels=["High", "Average", "At-Risk"])
            cm_list = cm.tolist() # [[TP, FP...]]
        else:
            cm_list = []
            
        # Store metrics in database
        cursor.execute(
            """
            INSERT OR REPLACE INTO model_metrics 
            (model_name, accuracy, precision, recall, f1_score, cv_score, confusion_matrix, last_trained)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (name, float(acc), float(precision), float(recall), float(f1), float(cv_score), json.dumps(cm_list))
        )
        
    # 7b. Populate students table with predictions for the entire cohort
    print("Populating students database table with model predictions...")
    X_full_proc = preprocessor.transform(X)
    full_preds = champion_model.predict(X_full_proc)
    full_probs = champion_model.predict_proba(X_full_proc)
    
    classes_list = champion_model.classes_.tolist()
    
    # Reuse active connection to write student predictions
    cursor.execute("DELETE FROM students")
    
    for idx, row in df.iterrows():
        pred_label = full_preds[idx]
        class_idx = classes_list.index(pred_label)
        conf = float(full_probs[idx][class_idx])
        
        cursor.execute(
            """
            INSERT INTO students (
                student_id, attendance, study_hours, assignment_completion,
                previous_grade, class_participation, family_support,
                parental_education, internet_access, extra_activities,
                predicted_category, confidence, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                row["Student_ID"],
                float(row["Attendance"]),
                float(row["Study_Hours"]),
                float(row["Assignment_Completion"]),
                float(row["Previous_Grade"]),
                float(row["Class_Participation"]),
                row["Family_Support"],
                row["Parental_Education"],
                row["Internet_Access"],
                row["Extra_Activities"],
                pred_label,
                conf
            )
        )
    conn.commit()
    conn.close()
    # 8. Serialize Preprocessor and Champion Model
    joblib.dump(preprocessor, os.path.join(MODEL_DIR, "preprocessing.pkl"))
    joblib.dump(champion_model, os.path.join(MODEL_DIR, "model.pkl"))
    print("Preprocessors and models successfully serialized to model directory.")
    
    # Save a JSON file detailing splits count
    split_info = {
        "train_records": len(X_train),
        "val_records": len(X_val),
        "test_records": len(X_test),
        "features": preprocessor.get_feature_names()
    }
    with open(os.path.join(MODEL_DIR, "split_info.json"), "w") as f:
        json.dump(split_info, f, indent=4)

if __name__ == "__main__":
    train_and_evaluate_models()
