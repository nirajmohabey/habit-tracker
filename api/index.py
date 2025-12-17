import sys
import os

# Mark as Vercel environment
os.environ['VERCEL'] = '1'

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Flask app
try:
    from app import app
except Exception as e:
    # Log error for debugging
    import traceback
    print(f"Error importing app: {e}")
    print(traceback.format_exc())
    raise

# Vercel Python runtime automatically handles Flask apps
# Just export the app - @vercel/python will wrap it
