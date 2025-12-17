# Vercel serverless function for Flask app
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set Vercel environment flag
os.environ['VERCEL'] = '1'

# Import Flask app with error handling
try:
    from app import app
    print("Flask app imported successfully")
except Exception as e:
    print(f"Error importing Flask app: {e}")
    import traceback
    traceback.print_exc()
    # Create a minimal error app
    from flask import Flask, jsonify
    app = Flask(__name__)
    @app.route('/<path:path>')
    @app.route('/')
    def error_handler(path=''):
        return jsonify({
            'error': 'Failed to initialize application',
            'message': str(e),
            'path': path
        }), 500

# Export app for Vercel
# The @vercel/python builder automatically handles Flask WSGI apps
