import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

NUMERICAL_FEATURES = [
    "Attendance",
    "Study_Hours",
    "Assignment_Completion",
    "Previous_Grade",
    "Class_Participation"
]

CATEGORICAL_FEATURES = [
    "Family_Support",
    "Parental_Education",
    "Internet_Access",
    "Extra_Activities"
]

ALL_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES

def create_preprocessing_pipeline():
    """
    Creates and returns a ColumnTransformer preprocessing pipeline.
    """
    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])
    
    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERICAL_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES)
        ]
    )
    
    return preprocessor

class StudentDataPreprocessor:
    """
    A wrapper class around ColumnTransformer to facilitate fit, transform,
    and extraction of feature names.
    """
    def __init__(self):
        self.pipeline = create_preprocessing_pipeline()
        self.feature_names_ = None
        self.is_fitted = False
        
    def fit(self, X, y=None):
        # Validate that all required features exist in X
        X_subset = X[ALL_FEATURES]
        self.pipeline.fit(X_subset)
        self.is_fitted = True
        
        # Determine feature names after transformations
        # For numeric, name remains same
        num_cols = NUMERICAL_FEATURES
        # For categorical, retrieve from onehot encoder
        cat_encoder = self.pipeline.named_transformers_["cat"].named_steps["onehot"]
        cat_cols = []
        for i, col in enumerate(CATEGORICAL_FEATURES):
            cats = cat_encoder.categories_[i]
            cat_cols.extend([f"{col}_{cat}" for cat in cats])
            
        self.feature_names_ = num_cols + cat_cols
        return self
        
    def transform(self, X):
        if not self.is_fitted:
            raise ValueError("The preprocessor must be fitted before transforming data.")
        X_subset = X[ALL_FEATURES]
        return self.pipeline.transform(X_subset)
        
    def fit_transform(self, X, y=None):
        self.fit(X, y)
        return self.transform(X)

    def get_feature_names(self):
        return self.feature_names_
