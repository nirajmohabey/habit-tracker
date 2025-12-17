# Vercel serverless function for Flask app
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set Vercel environment flag
os.environ['VERCEL'] = '1'

# Import Flask app
from app import app

# Vercel Python runtime expects the app to be exported
# The @vercel/python builder handles WSGI automatically
