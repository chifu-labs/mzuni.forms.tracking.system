# PythonAnywhere WSGI entry point
# In your PythonAnywhere web tab, set the WSGI file to this file
# and the working directory to this project folder.
import sys
import os

# Add the project directory to the Python path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import create_app
application = create_app()
