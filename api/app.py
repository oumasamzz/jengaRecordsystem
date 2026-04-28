import os
import json
import firebase_admin
from flask import Flask, render_template, request, jsonify
from firebase_admin import credentials, storage, firestore

# --- PATH CONFIGURATION ---
# Ensures Flask finds templates regardless of Vercel's environment
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
                # strict=False handles newline characters in the private key
                cred_dict = json.loads(fb_config, strict=False)
                return firebase_admin.initialize_app(credentials.Certificate(cred_dict), {
                    'storageBucket': 'jenga-africa-xxx.appspot.com' # <--- UPDATE THIS
                })
            except Exception as e:
                print(f"Firebase Config Error: {e}")
        
        # Local Fallback
        local_path = os.path.join(api_dir, "serviceAccountKey.json")
        if os.path.exists(local_path):
            return firebase_admin.initialize_app(credentials.Certificate(local_path), {
                'storageBucket': 'jenga-africa-xxx.appspot.com' # <--- UPDATE THIS
            })
    return firebase_admin.get_app()

# Global Clients
try:
    firebase_app = initialize_firebase()
    db = firestore.client()
    bucket = storage.bucket()
except Exception as e:
    print(f"Initialization Failed: {e}")
    db = None
    bucket = None

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    if not db:
        return jsonify({"error": "Database not connected"}), 500
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
        return jsonify({"error": "Storage not connected"}), 500
    try:
        file = request.files.get('file')
        title = request.form.get('title')
        year = request.form.get('year')
        
        if not file:
            return jsonify({"error": "No file"}), 400
            
        # File type detection
        ext = file.filename.split('.')[-1].lower()
        
        blob = bucket.blob(f"reports/{file.filename}")
        blob.upload_from_file(file)
        blob.make_public()
        
        report_data = {
            "title": title,
            "year": year,
            "url": blob.public_url,
            "type": ext
        }
        db.collection('reports').add(report_data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete/<report_id>', methods=['DELETE'])
def delete(report_id):
    # Verify Admin Key
    if request.headers.get("X-Admin-Key") != "Tandy254./":
        return jsonify({"error": "Unauthorized"}), 403
        
    try:
        doc_ref = db.collection('reports').document(report_id)
        doc = doc_ref.get().to_dict()
        if doc:
            # Delete from Storage
            try:
                filename = doc['url'].split('/')[-1].split('?')[0]
                bucket.blob(f"reports/{filename}").delete()
            except: pass
            # Delete from Firestore
            doc_ref.delete()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)