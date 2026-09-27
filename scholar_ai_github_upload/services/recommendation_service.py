class RecommendationService:
    @staticmethod
    def get_recommendations(student_data, prediction, confidence):
        """
        Generates structured academic recommendations based on student metrics and risk level.
        """
        recommendations = []
        
        # Extract inputs
        attendance = float(student_data.get("Attendance", 0))
        study_hours = float(student_data.get("Study_Hours", 0))
        assignment_completion = float(student_data.get("Assignment_Completion", 0))
        previous_grade = float(student_data.get("Previous_Grade", 0))
        class_participation = float(student_data.get("Class_Participation", 0))
        
        # Rule-based metrics checks
        if attendance < 75.0:
            recommendations.append({
                "metric": "Attendance",
                "value": f"{attendance}%",
                "recommendation": f"Improve class attendance to at least 75% (currently {attendance}%). Consistent presence is essential for concept mastery.",
                "action": "Set a daily alarm and review attendance weekly."
            })
            
        if study_hours < 8.0:
            recommendations.append({
                "metric": "Study Hours",
                "value": f"{study_hours} hrs/wk",
                "recommendation": f"Increase weekly independent study time to 8+ hours (currently {study_hours} hours). Set a dedicated study schedule.",
                "action": "Create a structured study timetable, aiming for 1.5 - 2 hours per day."
            })
            
        if assignment_completion < 75.0:
            recommendations.append({
                "metric": "Assignment Completion",
                "value": f"{assignment_completion}%",
                "recommendation": f"Complete and submit pending assignments to reach 80%+ completion rate (currently {assignment_completion}%).",
                "action": "List all outstanding coursework and submit at least one overdue assignment by this weekend."
            })
            
        if previous_grade < 65.0:
            recommendations.append({
                "metric": "Previous Grade",
                "value": f"{previous_grade}%",
                "recommendation": f"Access extra academic support or peer tutoring to review weak areas (previous grade was {previous_grade}%).",
                "action": "Join a student study group or attend weekly teacher office hours."
            })
            
        if class_participation < 60.0:
            recommendations.append({
                "metric": "Class Participation",
                "value": f"{class_participation}%",
                "recommendation": f"Engage more actively in class discussions and interactive activities (participation rated at {class_participation}%).",
                "action": "Commit to asking or answering at least one question during every class session."
            })
            
        # General recommendations based on risk classification
        if prediction == "At-Risk":
            # Early Intervention Checklist
            recommendations.append({
                "metric": "Academic Mentorship",
                "value": "At-Risk Status",
                "recommendation": "Schedule a teacher mentoring session immediately to draft an individual learning plan.",
                "action": "Book a 15-minute consultation with the course instructor."
            })
            recommendations.append({
                "metric": "Performance Monitoring",
                "value": "At-Risk Status",
                "recommendation": "Conduct weekly performance monitoring checks to track study hours and assignment progress.",
                "action": "Use a study-tracking app to log daily academic progress."
            })
        elif prediction == "Average" and len(recommendations) == 0:
            # If student is average but meets all indicators, give positive reinforcement
            recommendations.append({
                "metric": "Progress Check",
                "value": "Average Status",
                "recommendation": "Maintain the current workload but seek challenge topics to push into the High performance bracket.",
                "action": "Ask for extra-credit tasks or review advanced course material."
            })
        elif prediction == "High" and len(recommendations) == 0:
            recommendations.append({
                "metric": "Academic Enrichment",
                "value": "High Status",
                "recommendation": "Student is performing exceptionally well. Encourage peer tutoring or advanced placement exercises.",
                "action": "Offer to mentor classmates or explore advanced research topics in the subject."
            })
            
        # Disclaimer text required by guidelines:
        # "Do not present recommendations as medical, psychological, or guaranteed outcomes."
        disclaimer = "Note: These recommendations are educational guidelines based on historical student performance data. They are designed to support academic planning and do not guarantee specific grade outcomes."
        
        return {
            "list": recommendations,
            "disclaimer": disclaimer
        }
