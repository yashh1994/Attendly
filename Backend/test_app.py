from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from database import db, jwt

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'test-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
jwt.init_app(app)
CORS(app)

with app.app_context():
    # Import models within app context
    from models.models import User, Class, FaceData, AttendanceSession, AttendanceRecord, ClassEnrollment
    
    # Create tables
    db.create_all()
    print('✅ Database tables created successfully')

from routes.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/api/auth')

print('✅ Flask app configured successfully')
print('📋 Registered routes:')
for rule in app.url_map.iter_rules():
    print(f'  {rule.methods} {rule.rule}')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)