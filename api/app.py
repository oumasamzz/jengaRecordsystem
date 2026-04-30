import os
from flask import Flask, render_template, request, jsonify
from imagekitio import ImageKit

# Standard Vercel pathing for templates
api_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(api_dir)
template_dir = os.path.join(project_root, 'templates')

app = Flask(__name__, template_folder=template_dir)

# --- IMAGEKIT INITIALIZATION (V4+ SECURE VERSION) ---
def get_ik():
    # Fetch from Vercel Environment Variables
    pub = os.environ.get("IK_PUBLIC_KEY")
    pri = os.environ.get("IK_PRIVATE_KEY")
    url = os.environ.get("IK_URL_ENDPOINT")
    
    if not all([pub, pri, url]):
        print("ERROR: Missing Environment Variables in Vercel!")
        return None
    
    try:
        # The most stable initialization for the current imagekitio library
        return ImageKit(
            private_key=pri,
            public_key=pub,
            url_endpoint=url
        )
    except Exception as e:
        print(f"FAILED TO INITIALIZE IMAGEKIT: {e}")
        return None

ik = get_ik()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    if not ik:
        return jsonify({"error": "Backend config missing"}), 500
    try:
        # Fetch files from the root or 'reports' folder
        # The SDK returns a list of file objects
        list_files = ik.list_files({"path": "/"})
        
        reports_list = []
        for f in list_files:
            # Only include files that have our metadata tags [Title, Year]
            if f.tags and len(f.tags) >= 1:
                reports_list.append({
                    "id": f.file_id,
                    "title": f.tags[0],
                    "year": f.tags[1] if len(f.tags) > 1 else "2026",
                    "url": f.url,
                    "type": f.name.split('.')[-1].upper()
                })
        return jsonify(reports_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    if not ik:
        return jsonify({"error": "ImageKit not initialized. Check Environment Variables."}), 500
    try:
        file = request.files.get('file')
        title = request.form.get('title')
        year = request.form.get('year')

        if not file or not title:
            return jsonify({"error": "Missing file or title"}), 400

        file_content = file.read()
        file_name = file.filename

        # Strategy: Try both common SDK patterns to ensure compatibility
        try:
            # Pattern A: Standard SDK
            ik.upload_file(
                file=file_content,
                file_name=file_name,
                options={
                    "tags": [title, year],
                    "use_unique_file_name": True
                }
            )
        except AttributeError:
            # Pattern B: Newer SDK v4+ structure
            ik.files.upload(
                file=file_content,
                file_name=file_name,
                options={
                    "tags": [title, year],
                    "use_unique_file_name": True
                }
            )
        
        return jsonify({"success": True})
    except Exception as e:
        # This will print the EXACT error in your Vercel Logs
        print(f"UPLOAD CRASH: {str(e)}") 
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@app.route('/api/delete/<file_id>', methods=['DELETE'])
def delete(file_id):
    # Security check for deletion
    if request.headers.get("X-Admin-Key") != "Tandy254./":
        return jsonify({"error": "Unauthorized"}), 403
    try:
        ik.delete_file(file_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# For local testing
if __name__ == "__main__":
    app.run(debug=True)