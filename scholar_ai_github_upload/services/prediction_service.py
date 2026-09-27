import os
import joblib
import pandas as pd
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model")

class PredictionService:
    def __init__(self):
        self.model_path = os.path.join(MODEL_DIR, "model.pkl")
        self.preprocessor_path = os.path.join(MODEL_DIR, "preprocessing.pkl")
        self.model = None
        self.preprocessor = None
        
    def _load_model_and_preprocessor(self):
        if not os.path.exists(self.model_path) or not os.path.exists(self.preprocessor_path):
            raise FileNotFoundError("Model or Preprocessor file not found. Please train the model first.")
        
        if self.model is None:
            self.model = joblib.load(self.model_path)
        if self.preprocessor is None:
            self.preprocessor = joblib.load(self.preprocessor_path)
            
    def predict(self, student_data):
        """
        student_data: dict containing keys:
            - Attendance (float, 0-100)
            - Study_Hours (float, 0-100)
            - Assignment_Completion (float, 0-100)
            - Previous_Grade (float, 0-100)
            - Class_Participation (float, 0-100)
            - Family_Support (str)
            - Parental_Education (str)
            - Internet_Access (str)
            - Extra_Activities (str)
        """
        self._load_model_and_preprocessor()
        
        # Convert single record dict to DataFrame
        df = pd.DataFrame([student_data])
        
        # Preprocess features
        X_proc = self.preprocessor.transform(df)
        
        # Predict class and probabilities
        pred_class = self.model.predict(X_proc)[0]
        prob = self.model.predict_proba(X_proc)[0]
        
        # Map probabilities to classes
        classes = self.model.classes_
        class_probs = {cls: float(prob[i]) for i, cls in enumerate(classes)}
        
        # Sort classes to make sure we return consistent order
        probs_dict = {
            "High": class_probs.get("High", 0.0),
            "Average": class_probs.get("Average", 0.0),
            "At-Risk": class_probs.get("At-Risk", 0.0)
        }
        
        # Confidence score is the probability of the predicted class
        confidence = probs_dict[pred_class]
        
        # Retrieve feature importances from model
        importances = self.model.feature_importances_
        feature_names = self.preprocessor.get_feature_names()
        
        # Combine feature names with importances
        global_importance = []
        for name, imp in zip(feature_names, importances):
            global_importance.append({"feature": name, "importance": float(imp)})
        global_importance = sorted(global_importance, key=lambda x: x["importance"], reverse=True)
        
        # Compute student-specific contributing features/risk factors
        # Look at numerical features and see if they are below median thresholds
        # Benchmark averages:
        benchmarks = {
            "Attendance": 75.0,
            "Study_Hours": 10.0,
            "Assignment_Completion": 70.0,
            "Previous_Grade": 65.0,
            "Class_Participation": 60.0
        }
        
        student_performance_factors = []
        for feat, val in benchmarks.items():
            st_val = float(student_data.get(feat, 0))
            importance_weight = next((x["importance"] for x in global_importance if x["feature"] == feat), 0.05)
            
            # Distance from benchmark
            diff = st_val - val
            # Factor impact: negative means it's a risk factor, positive means a strength
            impact = diff * importance_weight
            
            student_performance_factors.append({
                "feature": feat,
                "value": st_val,
                "benchmark": val,
                "impact": float(impact),
                "type": "Strength" if impact >= 0 else "Risk Factor"
            })
            
        student_performance_factors = sorted(student_performance_factors, key=lambda x: x["impact"])
        
        return {
            "prediction": pred_class,
            "confidence": confidence,
            "probabilities": probs_dict,
            "global_feature_importance": global_importance[:10], # top 10
            "performance_factors": student_performance_factors
        }
        
    def get_model_features(self):
        self._load_model_and_preprocessor()
        importances = self.model.feature_importances_
        feature_names = self.preprocessor.get_feature_names()
        
        # Aggregate one-hot encoded columns back to original variables for cleaner charts
        aggregated = {
            "Attendance": 0.0,
            "Previous Grade": 0.0,
            "Study Hours": 0.0,
            "Assignments": 0.0,
            "Class Participation": 0.0,
            "Family Support": 0.0,
            "Parental Education": 0.0,
            "Internet Access": 0.0,
            "Extra Activities": 0.0
        }
        
        for name, imp in zip(feature_names, importances):
            if "Attendance" in name:
                aggregated["Attendance"] += imp
            elif "Previous_Grade" in name:
                aggregated["Previous Grade"] += imp
            elif "Study_Hours" in name:
                aggregated["Study Hours"] += imp
            elif "Assignment_Completion" in name:
                aggregated["Assignments"] += imp
            elif "Class_Participation" in name:
                aggregated["Class Participation"] += imp
            elif "Family_Support" in name:
                aggregated["Family Support"] += imp
            elif "Parental_Education" in name:
                aggregated["Parental Education"] += imp
            elif "Internet_Access" in name:
                aggregated["Internet Access"] += imp
            elif "Extra_Activities" in name:
                aggregated["Extra Activities"] += imp
                
        # Format as list of dicts sorted by importance
        results = [{"feature": k, "importance": float(v)} for k, v in aggregated.items()]
        results = sorted(results, key=lambda x: x["importance"], reverse=True)
        return results
