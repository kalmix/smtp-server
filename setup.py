import os
from dotenv import load_dotenv, set_key
import secrets
import string
import subprocess
import sys
from yaspin import yaspin
from yaspin.spinners import Spinners
import inquirer
from inquirer.themes import GreenPassion
import pyfiglet
from colorama import init, Fore, Style
import time
import threading

def generate_secret_key(length=32):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_api_token(length=48):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def run_pip_install():
    try:
        print(Fore.YELLOW + "\nInstalling requirements..." + Style.RESET_ALL)
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"\nError installing requirements: {e.stderr.decode()}" + Style.RESET_ALL)
        return False
    except FileNotFoundError:
        print(Fore.RED + "\nError: requirements.txt not found!" + Style.RESET_ALL)
        return False

def write_env_file(env_vars):
    try:
        for key, value in env_vars.items():
            set_key('.env', key, value)
        return True
    except Exception as e:
        print(Fore.RED + f"\nError writing to .env file: {str(e)}" + Style.RESET_ALL)
        return False

def run_server():
    try:
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nServer stopped" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"\nServer error: {str(e)}" + Style.RESET_ALL)

def setup_environment():
    # Initialize colorama
    init()
    
    # Display ASCII art header
    header = pyfiglet.figlet_format("Form API Setup")
    print(Fore.GREEN + header + Style.RESET_ALL)
    
    # Create .env file if it doesn't exist
    try:
        if not os.path.exists('.env'):
            with open('.env', 'w') as f:
                f.write('')
        load_dotenv()
    except Exception as e:
        print(Fore.RED + f"Error creating .env file: {str(e)}" + Style.RESET_ALL)
        return False

    # Prepare questions
    questions = [
        inquirer.Text('GMAIL_USER', 
                     message="Enter your Gmail address",
                     validate=lambda _, x: '@' in x),
        inquirer.Password('GMAIL_PASSWORD',
                         message="Enter your Gmail app password"),
        inquirer.Text('ALLOWED_ORIGINS',
                     message="Enter allowed origins (comma-separated)",
                     default="http://localhost:3000"),
        inquirer.Text('API_VERSION',
                     message="Enter API version",
                     default="1.0.0"),
        inquirer.Text('PORT',
                     message="Enter port number for the server",
                     default="5000"),
        inquirer.Confirm('START_SERVER',
                        message="Would you like to start the server after setup?",
                        default=True),
    ]

    try:
        # Ask questions
        print(Fore.CYAN + "\nPlease provide the following information:" + Style.RESET_ALL)
        answers = inquirer.prompt(questions, theme=GreenPassion())
        
        if not answers:
            print(Fore.RED + "\nSetup cancelled by user" + Style.RESET_ALL)
            return False

        # Generate secrets
        print(Fore.YELLOW + "\nGenerating secure keys..." + Style.RESET_ALL)
        secret_key = generate_secret_key()
        api_token = generate_api_token()
        
        # Prepare environment variables
        env_vars = {
            'FLASK_SECRET_KEY': secret_key,
            'API_TOKEN': api_token,
            'API_VERSION': answers['API_VERSION'],
            'GMAIL_USER': answers['GMAIL_USER'],
            'GMAIL_PASSWORD': answers['GMAIL_PASSWORD'],
            'ALLOWED_ORIGINS': answers['ALLOWED_ORIGINS'],
            'PORT': answers['PORT']
        }

        # Write to .env file
        print(Fore.YELLOW + "\nSaving configuration..." + Style.RESET_ALL)
        if not write_env_file(env_vars):
            return False

        # Install requirements
        if not run_pip_install():
            return False

        # Setup completed successfully
        print(Fore.GREEN + "\n✅ Setup completed successfully!" + Style.RESET_ALL)
        print(Fore.YELLOW + "\nYour API Token (keep this secure):" + Style.RESET_ALL)
        print(Fore.GREEN + api_token + Style.RESET_ALL)
        
        if answers['START_SERVER']:
            print(Fore.CYAN + f"\nStarting server on port {answers['PORT']}..." + Style.RESET_ALL)
            run_server()
        else:
            print(Fore.CYAN + "\nTo start the API server, run:" + Style.RESET_ALL)
            print(Fore.WHITE + "python app.py" + Style.RESET_ALL)
        
        return True

    except KeyboardInterrupt:
        print(Fore.RED + "\n\nSetup interrupted by user" + Style.RESET_ALL)
        return False
    except Exception as e:
        print(Fore.RED + f"\nAn unexpected error occurred: {str(e)}" + Style.RESET_ALL)
        return False

if __name__ == '__main__':
    success = setup_environment()
    sys.exit(0 if success else 1)