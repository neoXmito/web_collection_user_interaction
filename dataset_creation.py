# dataset_creation.py
import pandas as pd
from sqlalchemy import func, case
from app import app, db, CaptchaAttempt, Interaction

def create_dataset():
    with app.app_context():
        # Query base attempt data
        attempts = CaptchaAttempt.query.all()
        
        dataset = []
        
        for attempt in attempts:
            # Get all interactions for this attempt
            interactions = Interaction.query.filter_by(attempt_id=attempt.id).all()
            
            # Calculate interaction metrics
            mouse_events = [i for i in interactions if i.type == 'mousemove']
            click_events = [i for i in interactions if i.type == 'click']
            key_events = [i for i in interactions if i.type == 'keydown']
            input_changes = [i for i in interactions if i.type == 'input_change']
            
            # Calculate mouse movement statistics
            mouse_speeds = [i.speed for i in mouse_events if i.speed is not None]
            
            # Calculate time-based features
            total_time = attempt.end_time - attempt.start_time
            
            # Create feature dictionary
            features = {
                'attempt_id': attempt.id,
                'success': attempt.success,
                'correct_answer': attempt.correct_answer,
                'user_answer': attempt.user_answer,
                'total_time': total_time,
                
                # Mouse metrics
                'mouse_move_count': len(mouse_events),
                'avg_mouse_speed': sum(mouse_speeds)/len(mouse_speeds) if mouse_speeds else 0,
                'max_mouse_speed': max(mouse_speeds) if mouse_speeds else 0,
                
                # Click metrics
                'click_count': len(click_events),
                'avg_click_interval': total_time / len(click_events) if click_events else 0,
                
                # Keyboard metrics
                'keypress_count': len(key_events),
                'backspace_count': sum(1 for k in key_events if k.key == 'Backspace'),
                
                # Input metrics
                'input_change_count': len(input_changes),
                'final_input_length': len(attempt.user_answer),
                'edit_distance': levenshtein(attempt.correct_answer, attempt.user_answer),
                
                # Temporal features
                'time_per_character': total_time / len(attempt.user_answer) if attempt.user_answer else 0,
                
                # Additional features
                'error_rate': len(input_changes) / len(attempt.user_answer) if attempt.user_answer else 0
            }
            
            dataset.append(features)
        
        # Convert to DataFrame
        df = pd.DataFrame(dataset)
        
        # Save to CSV
        df.to_csv('dataset\captcha_dataset.csv', index=False)
        return df

def levenshtein(s1, s2):
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

if __name__ == '__main__':
    df = create_dataset()
    print(f"Dataset created with {len(df)} entries")
    print(df.head())
    #df.to_csv('dataset\captcha_dataset.csv', index=False)