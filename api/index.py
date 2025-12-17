"""
Vercel serverless function entry point
This is the main handler for Vercel's serverless environment
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app

# Vercel expects the app to be accessible
# Export the Flask app for Vercel
handler = app
