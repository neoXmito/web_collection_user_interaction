from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import random
import time

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///captcha_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Database models
class CaptchaAttempt(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    correct_answer = db.Column(db.String(50))
    user_answer = db.Column(db.String(50))
    success = db.Column(db.Boolean)
    start_time = db.Column(db.Float)
    end_time = db.Column(db.Float)
    interactions = db.relationship('Interaction', backref='attempt', lazy=True)

class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.String(20), db.ForeignKey('captcha_attempt.id'))
    type = db.Column(db.String(20))
    x = db.Column(db.Float)
    y = db.Column(db.Float)
    key = db.Column(db.String(10))
    speed = db.Column(db.Float)
    timestamp = db.Column(db.Float)
    extra_data = db.Column(db.JSON)

# Configuration
CAPTCHA_IMAGES_DIR = 'captcha_images'
current_captchas = {}  # Stores {captcha_id: answer}

def get_random_captcha():
    """Get random CAPTCHA image and create new entry"""
    images = os.listdir(CAPTCHA_IMAGES_DIR)
    if not images:
        return None, None
    selected = random.choice(images)
    captcha_id = str(int(time.time() * 1000))  # High precision ID
    answer = os.path.splitext(selected)[0]
    current_captchas[captcha_id] = answer
    return captcha_id, selected

@app.route('/')
def index():
    """Main page with CAPTCHA"""
    captcha_id, filename = get_random_captcha()
    if not filename:
        return "No CAPTCHA images found", 404
    return render_template('index.html',
                         captcha_id=captcha_id,
                         captcha_image=filename)

@app.route('/captcha_images/<path:filename>')
def serve_captcha(filename):
    """Serve CAPTCHA images"""
    return send_from_directory(CAPTCHA_IMAGES_DIR, filename)

@app.route('/verify', methods=['POST'])
def verify():
    """Verify CAPTCHA answer"""
    data = request.json
    captcha_id = data.get('captcha_id')
    user_answer = data.get('answer', '').strip().lower()
    
    # Get stored answer
    correct_answer = current_captchas.get(captcha_id, '').lower()
    success = user_answer == correct_answer
    
    # Create database records
    attempt = CaptchaAttempt(
        id=captcha_id,
        correct_answer=correct_answer,
        user_answer=user_answer,
        success=success,
        start_time=data.get('start_time'),
        end_time=data.get('end_time')
    )
    
    interactions = []
    for interaction in data.get('interactions', []):
        interactions.append(Interaction(
            attempt_id=captcha_id,
            type=interaction.get('type'),
            x=interaction.get('x'),
            y=interaction.get('y'),
            key=interaction.get('key'),
            speed=interaction.get('speed'),
            timestamp=interaction.get('timestamp'),
            extra_data=interaction.get('extra_data')
        ))
    
    db.session.add(attempt)
    db.session.add_all(interactions)
    db.session.commit()
    
    # Remove used CAPTCHA
    if captcha_id in current_captchas:
        del current_captchas[captcha_id]
    
    return jsonify({'success': success})

@app.route('/get_new_captcha')
def new_captcha():
    """Get new CAPTCHA for client-side refresh"""
    captcha_id, filename = get_random_captcha()
    if not filename:
        return jsonify(error="No CAPTCHA available"), 404
    
    return jsonify({
        'captcha_id': captcha_id,
        'image_url': f"/captcha_images/{filename}"
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)