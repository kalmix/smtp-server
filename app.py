from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
import time
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

# Configure CORS
allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Form API startup')

# Rate limiting configuration
RATE_LIMIT = 1  # seconds
rate_limit_data = {}

def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({
                'error': 'No token provided',
                'message': 'Authorization token is required'
            }), 401
            
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        if token != os.getenv('API_TOKEN'):
            return jsonify({
                'error': 'Invalid token',
                'message': 'The provided token is invalid'
            }), 403
            
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_time = time.time()
        
        if ip in rate_limit_data:
            last_request_time = rate_limit_data[ip]
            if current_time - last_request_time < RATE_LIMIT:
                return jsonify({
                    'error': 'Too many requests',
                    'message': f'Please wait {RATE_LIMIT} seconds between submissions'
                }), 429
        
        rate_limit_data[ip] = current_time
        return f(*args, **kwargs)
    return decorated_function

def send_email(form_data, recipient_email=None):
    """Send email using Gmail SMTP"""
    sender_email = os.getenv('GMAIL_USER')
    sender_password = os.getenv('GMAIL_PASSWORD')
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email if recipient_email else sender_email
    msg['Subject'] = 'New Form Submission'
    
    # Create HTML body
    html = "<h2>New Form Submission</h2><table>"
    for key, value in form_data.items():
        html += f"<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>"
    html += "</table>"
    
    msg.attach(MIMEText(html, 'html'))
    
    # Send email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        app.logger.error(f'Email sending failed: {str(e)}')
        return False

@app.route('/api/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': os.getenv('API_VERSION', '1.0.0')
    })

@app.route('/api/submit-form', methods=['POST'])
@require_token
@rate_limit
def submit_form():
    """Handle form submission"""
    try:
        # Get form data
        form_data = request.get_json()
        
        if not form_data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Please provide form data'
            }), 400
        
        # Log submission
        app.logger.info(f'Form submission received from {request.remote_addr}')
        
        # Get optional recipient email from request headers
        recipient_email = request.headers.get('X-Forward-Email')
        
        # Send email
        email_sent = send_email(form_data, recipient_email)
        
        if not email_sent:
            return jsonify({
                'error': 'Email sending failed',
                'message': 'Form submitted but notification email failed'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Form submitted successfully'
        })
        
    except Exception as e:
        app.logger.error(f'Form submission error: {str(e)}')
        return jsonify({
            'error': 'Server error',
            'message': 'An unexpected error occurred'
        }), 500

@app.route('/api/forward-email', methods=['POST'])
@require_token
def forward_email():
    """Forward form submission to another email"""
    try:
        data = request.get_json()
        
        if not data or 'form_data' not in data or 'email' not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Please provide form_data and email'
            }), 400
            
        email_sent = send_email(data['form_data'], data['email'])
        
        if not email_sent:
            return jsonify({
                'error': 'Email forwarding failed',
                'message': 'Failed to forward email'
            }), 500
            
        return jsonify({
            'success': True,
            'message': 'Email forwarded successfully'
        })
        
    except Exception as e:
        app.logger.error(f'Email forwarding error: {str(e)}')
        return jsonify({
            'error': 'Server error',
            'message': 'An unexpected error occurred'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))