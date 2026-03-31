import sys
import os

# This file is used for deployment on PythonAnywhere.
# It ensures the project directory is in the system path so Flask can find your app.

# MANUALLY UPDATE THIS PATH to your project folder on PythonAnywhere
# Example: '/home/yourusername/qa-pramaan-automation'
project_home = os.path.dirname(os.path.abspath(__file__))

if project_home not in sys.path:
    sys.path.append(project_home)

# Set up the environment variable PythonAnywhere looks for
os.environ['PYTHONANYWHERE_DOMAIN'] = 'true'

from app import app as application
