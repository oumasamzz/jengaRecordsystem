import os
from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, storage, firestore

app = Flask(__name__, 
            template_folder='../templates', 
            static_folder='../static')

# 1. Initialize Firebase
# Make sure your JSON key is in the same folder
cred = credentials.Certificate("serviceAccountKey.json") 
firebase_admin.initialize_app(cred, {
    'storageBucket': 'your-project-id.appspot.com' # Found in Firebase Storage console
})

db = firestore.client()
bucket = storage.bucket()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    # Fetch report metadata from Firestore
    reports_ref = db.collection('reports')
    docs = reports_ref.stream()
    reports_list = [doc.to_dict() | {"id": doc.id} for doc in docs]
    return jsonify(reports_list)

@app.route('/api/upload', methods=['POST'])
def upload():
    file = request.files['file']
    title = request.form.get('title')
    year = request.form.get('year')
    
    # 2. Upload actual file to Firebase Storage
    blob = bucket.blob(f"reports/{file.filename}")
    blob.upload_from_file(file)
    blob.make_public() # So visitors can download it
    
    # 3. Save metadata to Firestore
    report_data = {
        "title": title,
        "year": year,
        "url": blob.public_url,
        "type": file.filename.split('.')[-1]
    }
    db.collection('reports').add(report_data)
    
    return jsonify({"success": True})

@app.route('/api/delete/<report_id>', methods=['DELETE'])
def delete(report_id):
    # Check for a secret header
    admin_key = request.headers.get("X-Admin-Key")
    if admin_key != "Tandy254./": # Change this to your own secret
        return jsonify({"error": "Unauthorized"}), 403