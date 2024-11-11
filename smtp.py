import os
from dotenv import load_dotenv, set_key
import pyfiglet
from colorama import init, Fore, Style
import inquirer
from inquirer.themes import GreenPassion
import secrets
import string
import subprocess
import sys
from yaspin import yaspin
from yaspin.spinners import Spinners
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Initialize colorama
init()

# Create themed prompt
prompt = inquirer.prompt
def themed_prompt(questions): return prompt(questions, theme=GreenPassion())


def print_banner():
    """Display a stylish banner"""
    os.system('cls' if os.name == 'nt' else 'clear')
    font = pyfiglet.Figlet(font='slant')
    banner = font.renderText('Form API Setup')
    print(Fore.CYAN + banner + Style.RESET_ALL)
    print(Fore.YELLOW + "=" * 50 + Style.RESET_ALL)
    print(Fore.GREEN + " Server Configuration Wizard" + Style.RESET_ALL)
    print(Fore.YELLOW + "=" * 50 + Style.RESET_ALL + "\n")


def generate_api_key(length=32):
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_email(_, email):
    """Validate email format"""
    import re
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise inquirer.errors.ValidationError(
            '', reason='Please enter a valid email address')
    return True


def test_gmail_credentials(username, password):
    """Test Gmail credentials"""
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(username, password)
        server.quit()
        return True
    except:
        return False


def generate_server_file():
    """Generate the Flask server file"""
    server_code = '''
from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS
cors = CORS(app, resources={
    r"/*": {
        "origins": [
            "https://elenapallets.com.do",
            # Localhost regex pattern to match any port
            r"http://localhost:[0-9]+"
        ],
        "methods": ["POST", "GET", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key"]
    }
})

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("GMAIL_USERNAME")
SMTP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
PORT = int(os.getenv("PORT", 5000))

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == os.getenv("API_KEY"):
            return f(*args, **kwargs)
        return jsonify({"error": "Invalid or missing API key"}), 401
    return decorated_function

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

@app.route('/submit-form', methods=['POST'])
@require_api_key
def submit_form():
    try:
        form_data = request.form.to_dict()
        
        if not form_data:
            return jsonify({"error": "No form data received"}), 400
        
        email_body = "New Form Submission:\n\n"
        for key, value in form_data.items():
            email_body += f"{key}: {value}\n"

        success, message = send_email("New Form Submission", email_body)
        
        if success:
            return jsonify({"message": "Form submitted successfully"}), 200
        else:
            return jsonify({"error": f"Failed to send email: {message}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "email_configured": bool(SMTP_USERNAME and SMTP_PASSWORD)
    }), 200

if __name__ == '__main__':
    app.run(
        debug=os.getenv('ENVIRONMENT') == 'development',
        host='0.0.0.0',
        port=PORT
    )
'''

    try:
        with open('app.py', 'w') as f:
            f.write(server_code)
        return True
    except Exception as e:
        print(f"Error generating server file: {e}")
        return False


def setup_config():
    """Interactive configuration setup"""
    print_banner()

    # Load existing environment variables
    load_dotenv()

    # Get existing or generate new API key
    existing_api_key = os.getenv('API_KEY')
    if existing_api_key:
        print(Fore.YELLOW + "Found existing API key." + Style.RESET_ALL)
        api_key_choice = themed_prompt([
            inquirer.List('api_key_action',
                          message="What would you like to do with the API key?",
                          choices=[
                              ('Keep existing API key', 'keep'),
                              ('Generate new API key', 'new')
                          ])
        ])
        api_key = existing_api_key if api_key_choice['api_key_action'] == 'keep' else generate_api_key(
        )
    else:
        api_key = generate_api_key()

    # Common ports for web services
    common_ports = [
        '5000 (Default Flask)',
        '3000 (Common dev port)',
        '8080 (Alternative)',
        '8000 (Django default)',
        'Custom port'
    ]

    # Environment setup questions
    questions = [
        inquirer.List('environment',
                      message="Select your environment",
                      choices=[
                          ('Development (localhost)', 'development'),
                          ('Production (public server)', 'production')
                      ]),
        inquirer.List('port_choice',
                      message="Select server port",
                      choices=common_ports),
        inquirer.Text('custom_port',
                      message="Enter custom port number (1024-65535)",
                      validate=lambda _, x: x.isdigit() and 1024 <= int(x) <= 65535,
                      ignore=lambda x: x['port_choice'] != 'Custom port'),
        inquirer.List('email_service',
                      message="Select email service",
                      choices=[
                          ('Gmail (recommended)', 'gmail'),
                          ('Custom SMTP (advanced)', 'custom')
                      ]),
        inquirer.Text('gmail_username',
                      message="Enter your Gmail address",
                      validate=validate_email,
                      ignore=lambda x: x['email_service'] != 'gmail',
                      default=os.getenv('GMAIL_USERNAME', '')),
        inquirer.Password('gmail_password',
                          message="Enter your Gmail App Password (16-character)",
                          ignore=lambda x: x['email_service'] != 'gmail'),
        inquirer.Text('recipient_email',
                      message="Enter the email where you want to receive form submissions",
                      validate=validate_email,
                      default=os.getenv('RECIPIENT_EMAIL', ''))
    ]

    answers = themed_prompt(questions)

    # Handle port selection
    if answers['port_choice'] == 'Custom port':
        port = answers['custom_port']
    else:
        port = answers['port_choice'].split()[0]  # Get just the number

    # Test Gmail credentials if using Gmail
    if answers['email_service'] == 'gmail':
        with yaspin(Spinners.dots, text="Testing Gmail credentials...") as spinner:
            if test_gmail_credentials(answers['gmail_username'], answers['gmail_password']):
                spinner.ok("✓")
                print(
                    Fore.GREEN + "Gmail credentials verified successfully!" + Style.RESET_ALL)
            else:
                spinner.fail("×")
                print(Fore.RED + "Failed to verify Gmail credentials." +
                      Style.RESET_ALL)

                setup_choice = themed_prompt([
                    inquirer.List('action',
                                  message="What would you like to do?",
                                  choices=[
                                      ('Show Gmail setup instructions',
                                       'instructions'),
                                      ('Continue anyway', 'continue'),
                                      ('Start over', 'restart'),
                                      ('Exit', 'exit')
                                  ])
                ])

                if setup_choice['action'] == 'instructions':
                    print(Fore.YELLOW + "\nTo get an App Password:" +
                          Style.RESET_ALL)
                    print("1. Go to your Google Account settings")
                    print("2. Enable 2-Step Verification if not already enabled")
                    print("3. Go to Security → App passwords")
                    print("4. Generate a new app password for 'Mail'")
                    if not themed_prompt([inquirer.Confirm('continue', message="Continue with setup?", default=False)])['continue']:
                        return False
                elif setup_choice['action'] == 'restart':
                    return setup_config()
                elif setup_choice['action'] == 'exit':
                    return False

    # Save configuration
    with yaspin(Spinners.dots, text="Saving configuration...") as spinner:
        try:
            env_file = '.env'
            if answers['email_service'] == 'gmail':
                set_key(env_file, 'GMAIL_USERNAME', answers['gmail_username'])
                set_key(env_file, 'GMAIL_APP_PASSWORD',
                        answers['gmail_password'])
            set_key(env_file, 'RECIPIENT_EMAIL', answers['recipient_email'])
            set_key(env_file, 'API_KEY', api_key)
            set_key(env_file, 'PORT', port)
            set_key(env_file, 'ENVIRONMENT', answers['environment'])
            spinner.ok("✓")
        except Exception as e:
            spinner.fail("×")
            print(
                Fore.RED + f"Error saving configuration: {str(e)}" + Style.RESET_ALL)
            return False

    print(Fore.GREEN + "\n✨ Configuration saved successfully! ✨" + Style.RESET_ALL)
    print("\nHere's your API key (keep it secure):")
    print(Fore.YELLOW + f"\n{api_key}\n" + Style.RESET_ALL)

    print("To test your endpoint, use this curl command:")
    print(Fore.CYAN + f"""
curl -X POST \\
  -H "X-API-Key: {api_key}" \\
  -F "name=John Doe" \\
  -F "email=test@example.com" \\
  -F "message=Test message" \\
  http://localhost:{port}/submit-form
    """ + Style.RESET_ALL)

    return True


def main():
    try:
        if setup_config():
            # Generate server file
            with yaspin(Spinners.dots, text="Generating server file...") as spinner:
                if generate_server_file():
                    spinner.ok("✓")
                    print(
                        Fore.GREEN + "Server file generated successfully!" + Style.RESET_ALL)
                else:
                    spinner.fail("×")
                    print(Fore.RED + "Failed to generate server file." +
                          Style.RESET_ALL)
                    return

            # Show next steps
            start_server = themed_prompt([
                inquirer.List('action',
                              message="What would you like to do next?",
                              choices=[
                                  ('Start the server now', 'start'),
                                  ('View the API documentation', 'docs'),
                                  ('Exit', 'exit')
                              ])
            ])

            if start_server['action'] == 'start':
                # Check if Flask is installed
                try:
                    import flask
                except ImportError:
                    print(
                        Fore.YELLOW + "\nFlask is not installed. Installing required packages..." + Style.RESET_ALL)
                    subprocess.run([sys.executable, "-m", "pip",
                                   "install", "flask", "python-dotenv"])

                print(Fore.GREEN + "\nStarting server..." + Style.RESET_ALL)
                try:
                    subprocess.run([sys.executable, "app.py"])
                except Exception as e:
                    print(
                        Fore.RED + f"\nError starting server: {e}" + Style.RESET_ALL)

            elif start_server['action'] == 'docs':
                print(Fore.YELLOW + "\nAPI Documentation:" + Style.RESET_ALL)
                print("\nEndpoints:")
                print("  POST /submit-form")
                print("    - Required header: X-API-Key")
                print("    - Form fields: name, email, message")
                print("\nExample curl command:")
                print(f"curl -X POST -H \"X-API-Key: {os.getenv(
                    'API_KEY')}\" -F \"name=John Doe\" -F \"email=test@example.com\" -F \"message=Test message\" http://localhost:{os.getenv('PORT', '5000')}/submit-form")

    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\nSetup cancelled. Goodbye! 👋" + Style.RESET_ALL)
        sys.exit(0)


if __name__ == "__main__":
    main()
