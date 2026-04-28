import os
import json
from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, storage, firestore

# Initialize Flask with absolute pathing for Vercel
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, '../templates')

app = Flask(__name__, template_folder=template_dir)

# 1. Initialize Firebase (Vercel-Friendly Version)
if not firebase_admin._apps:
    firebase_config = os.environ.get("FIREBASE_CONFIG")
    
    if firebase_config:
        # If running on Vercel, use the Environment Variable
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
    else:
        # Fallback for local testing - ensure this file exists locally!
        cred = credentials.Certificate(os.path.join(base_dir, "serviceAccountKey.json"))

    firebase_admin.initialize_app(cred, {
        'storageBucket': 'your-project-id.appspot.com' # CHANGE THIS to your real bucket ID
    })

db = firestore.client()
bucket = storage.bucket()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    try:
        reports_ref = db.collection('reports')
        docs = reports_ref.stream()
        reports_list = [doc.to_dict() | {"id": doc.id} for doc in docs]
        return jsonify(reports_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file"}), 400
            
        file = request.files['file']
        title = request.form.get('title')
        year = request.form.get('year')
        
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
            # Extract filename from URL to delete from storage
            filename = doc['url'].split('/')[-1].split('?')[0]
            bucket.blob(f"reports/{filename}").delete()
            doc_ref.delete()
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Required for local testing only; Vercel ignores this
if __name__ == "__main__":
    app.run(debug=True)