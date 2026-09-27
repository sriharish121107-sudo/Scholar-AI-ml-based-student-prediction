import os
import pandas as pd
import numpy as np

def generate_student_dataset(output_path, num_records=1043, seed=42):
    np.random.seed(seed)
    
    # Generate student IDs
    student_ids = [f"S-{i:04d}" for i in range(1, num_records + 1)]
    
    # Generate numerical features
    attendance = np.random.uniform(50, 100, num_records)
    # Give some students very low attendance to simulate real-world risk profiles
    low_att_indices = np.random.choice(num_records, int(num_records * 0.15), replace=False)
    attendance[low_att_indices] = np.random.uniform(30, 60, len(low_att_indices))
    attendance = np.clip(attendance, 0, 100).round(1)
    
    study_hours = np.random.gamma(shape=5, scale=2, size=num_records) # peak around 10 hours
    study_hours = np.clip(study_hours, 1, 35).round(1)
    
    assignment_completion = np.random.uniform(60, 100, num_records)
    low_assign_indices = np.random.choice(num_records, int(num_records * 0.12), replace=False)
    assignment_completion[low_assign_indices] = np.random.uniform(20, 65, len(low_assign_indices))
    assignment_completion = np.clip(assignment_completion, 0, 100).round(1)
    
    previous_grade = np.random.normal(72, 12, num_records)
    previous_grade = np.clip(previous_grade, 30, 100).round(1)
    
    class_participation = np.random.uniform(40, 100, num_records)
    low_part_indices = np.random.choice(num_records, int(num_records * 0.1), replace=False)
    class_participation[low_part_indices] = np.random.uniform(10, 50, len(low_part_indices))
    class_participation = np.clip(class_participation, 0, 100).round(1)
    
    # Generate categorical features
    family_support_choices = ["Low", "Medium", "High"]
    family_support = np.random.choice(family_support_choices, num_records, p=[0.2, 0.4, 0.4])
    
    parental_edu_choices = ["High School", "Associate", "Bachelor", "Master", "PhD"]
    parental_education = np.random.choice(parental_edu_choices, num_records, p=[0.3, 0.25, 0.25, 0.15, 0.05])
    
    internet_access = np.random.choice(["Yes", "No"], num_records, p=[0.85, 0.15])
    extra_activities = np.random.choice(["Yes", "No"], num_records, p=[0.45, 0.55])
    
    # Calculate target score (academic performance index) with correlations
    # Scale variables internally 0-100 for score calculation
    att_score = attendance
    study_score = np.clip(study_hours * (100 / 30), 0, 100)
    assign_score = assignment_completion
    prev_grade_score = previous_grade
    part_score = class_participation
    
    # Base Score calculation
    score = (
        (att_score * 0.3) + 
        (assign_score * 0.25) + 
        (prev_grade_score * 0.2) + 
        (study_score * 0.15) + 
        (part_score * 0.1)
    )
    
    # Adjust score based on categorical factors
    for i in range(num_records):
        # Family Support
        if family_support[i] == "High":
            score[i] += 4
        elif family_support[i] == "Low":
            score[i] -= 4
            
        # Parental Education
        if parental_education[i] in ["Master", "PhD"]:
            score[i] += 3
        elif parental_education[i] == "High School":
            score[i] -= 2
            
        # Internet Access
        if internet_access[i] == "Yes":
            score[i] += 2
        else:
            score[i] -= 4
            
        # Extra Activities
        if extra_activities[i] == "Yes":
            score[i] += 1
            
    # Add noise
    noise = np.random.normal(0, 3, num_records)
    score += noise
    score = np.clip(score, 0, 100)
    
    # Classify into Performance Category
    performance_category = []
    for s in score:
        if s < 60:
            performance_category.append("At-Risk")
        elif s < 80:
            performance_category.append("Average")
        else:
            performance_category.append("High")
            
    # Create DataFrame
    df = pd.DataFrame({
        "Student_ID": student_ids,
        "Attendance": attendance,
        "Study_Hours": study_hours,
        "Assignment_Completion": assignment_completion,
        "Previous_Grade": previous_grade,
        "Class_Participation": class_participation,
        "Family_Support": family_support,
        "Parental_Education": parental_education,
        "Internet_Access": internet_access,
        "Extra_Activities": extra_activities,
        "Performance_Category": performance_category
    })
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Successfully generated {num_records} student records at: {output_path}")
    print(df["Performance_Category"].value_counts())

if __name__ == "__main__":
    generate_student_dataset("students.csv")
