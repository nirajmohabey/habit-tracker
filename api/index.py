import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import Flask app
from app import app

# Vercel Python runtime handler
# The @vercel/python builder automatically wraps Flask apps
