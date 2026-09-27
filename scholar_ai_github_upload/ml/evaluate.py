import os
import sys
import json
import sqlite3

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import DB_PATH

def print_evaluation_summary():
    if not os.path.exists(DB_PATH):
        print(f"Database at '{DB_PATH}' not found. Please train models first using: python ml/train.py")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT model_name, accuracy, precision, recall, f1_score, cv_score, last_trained FROM model_metrics")
        rows = cursor.fetchall()
        
        if not rows:
            print("No evaluation metrics found in the database. Please run: python ml/train.py")
            return
            
        print("\n" + "="*80)
        print("                 SCHOLAR AI - MODEL EVALUATION SUMMARY")
        print("="*80)
        print(f"{'Model Name':<25} | {'Accuracy':<10} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'5-Fold CV':<10}")
        print("-"*80)
        for row in rows:
            name, acc, prec, rec, f1, cv, last_t = row
            cv_str = f"{cv:.4f}" if cv > 0 else "N/A"
            print(f"{name:<25} | {acc:<10.4f} | {prec:<10.4f} | {rec:<10.4f} | {f1:<10.4f} | {cv_str:<10}")
        print("="*80)
        
        # Load split info if available
        split_info_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model", "split_info.json")
        if os.path.exists(split_info_path):
            with open(split_info_path, "r") as f:
                import json
                info = json.load(f)
                print(f"Dataset Split Sizes:")
                print(f"  Training records:   {info.get('train_records')}")
                print(f"  Validation records: {info.get('val_records')}")
                print(f"  Testing records:    {info.get('test_records')}")
                print(f"  Number of features: {len(info.get('features', []))}")
                print("="*80)
    except sqlite3.OperationalError as e:
        print(f"Error accessing database metrics: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print_evaluation_summary()
