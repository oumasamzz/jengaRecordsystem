import os
import json
import firebase_admin
from flask import Flask, render_template, request, jsonify
from firebase_admin import credentials, storage, firestore

# --- PATH FIXES ---
# Vercel needs absolute paths to find the templates folder from the api folder
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

# --- FIREBASE INITIALIZATION ---
def init_firebase():
    if not firebase_admin._apps:
        # Check Environment Variable first (For Vercel)
        fb_config = os.environ.get("FIREBASE_CONFIG")
        
        if fb_config:
            try:
                # Critical: strict=False handles potential whitespace issues in the JSON string
                cred_dict = json.loads(fb_config, strict=False)
                cred = credentials.Certificate(cred_dict)
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                return None
        else:
            # Fallback to local file (For Local Dev)
            # Make sure this file is inside your /api folder for local testing
            local_key = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            if os.path.exists(local_key):
                cred = credentials.Certificate(local_key)
            else:
                print("No Firebase Credentials found!")
                return None

        return firebase_admin.initialize_app(cred, {
            'storageBucket': 'jenga-africa-xxx.appspot.com' # REPLACE WITH YOUR ACTUAL BUCKET
        })

# Initialize safely
firebase_app = init_firebase()

# Only create clients if initialization succeeded
if firebase_app:
    db = firestore.client()
    bucket = storage.bucket()
else:
    db = None
    bucket = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    if not db:
        return jsonify({"error": "Database not initialized. Check Vercel Environment Variables."}), 500
    try:
        reports_ref = db.collection('reports')
        docs = reports_ref.stream()
        reports_list = [doc.to_dict() | {"id": doc.id} for doc in docs]
        return jsonify(reports_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    if not bucket:
        return jsonify({"error": "Storage not initialized"}), 500
    try:
        file = request.files.get('file')
        title = request.form.get('title')
        year = request.form.get('year')
        
        if not file:
            return jsonify({"error": "No file uploaded"}), 400
            
        blob = bucket.blob(f"reports/{file.filename}")
        blob.upload_from_file(file)
        blob.make_public()
        
        report_data = {
            "title": title,
            "year": year,
            "url": blob.public_url,
            "type": file.filename.split('.')[-1]
        }
        db.collection('reports').add(report_data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete/<report_id>', methods=['DELETE'])
def delete(report_id):
    admin_key = request.headers.get("X-Admin-Key")
    if admin_key != "Tandy254./":
        return jsonify({"error": "Unauthorized"}), 403
        
    try:
        doc_ref = db.collection('reports').document(report_id)
        doc = doc_ref.get().to_dict()
        
        if doc:
            # Storage delete
            try:
                filename = doc['url'].split('/')[-1].split('?')[0]
                bucket.blob(f"reports/{filename}").delete()
            except:
                pass # Continue if file is already gone
            
            doc_ref.delete()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Local development
if __name__ == "__main__":
    app.run(port=5000, debug=True)