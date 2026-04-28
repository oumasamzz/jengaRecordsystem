import os
import json
import firebase_admin
from flask import Flask, render_template, request, jsonify
from firebase_admin import credentials, storage, firestore

# --- ABSOLUTE PATHING ---
# Forces Flask to find templates regardless of Vercel's environment
api_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(api_dir)
template_dir = os.path.join(root_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

# --- FIREBASE BOOTSTRAP ---
def initialize_firebase():
    if not firebase_admin._apps:
        fb_config = os.environ.get("FIREBASE_CONFIG")
        if fb_config:
            try:
                # Use strict=False to ignore control characters in the JSON string
                cred_dict = json.loads(fb_config, strict=False)
                return firebase_admin.initialize_app(credentials.Certificate(cred_dict), {
                    'storageBucket': 'jenga-africa-xxx.appspot.com' # <--- DOUBLE CHECK THIS NAME
                })
            except Exception as e:
                print(f"FAILED TO LOAD ENV CONFIG: {e}")
        
        # Local Fallback
        local_path = os.path.join(api_dir, "serviceAccountKey.json")
        if os.path.exists(local_path):
            return firebase_admin.initialize_app(credentials.Certificate(local_path), {
                'storageBucket': 'jenga-africa-xxx.appspot.com'
            })
    return firebase_admin.get_app()

# Global Clients
try:
    firebase_app = initialize_firebase()
    db = firestore.client()
    bucket = storage.bucket()
except Exception as e:
    print(f"CRITICAL BOOT ERROR: {e}")
    db = None
    bucket = None

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

# HEALTH CHECK: Visit /api/health to verify the backend is up
@app.route('/api/health')
def health():
    status = "Connected" if db else "Firebase Connection Failed"
    return jsonify({"status": "Alive", "firebase": status})

@app.route('/api/reports', methods=['GET'])
def get_reports():
    if db is None:
        return jsonify({"error": "Backend running but Firebase not connected."}), 500
    try:
        reports_ref = db.collection('reports')
        docs = reports_ref.stream()
        reports_list = [doc.to_dict() | {"id": doc.id} for doc in docs]
        return jsonify(reports_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... keep your upload/delete routes from previous code ...