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
        # This will tell you if the variables are actually missing
        pub = os.environ.get("IK_PUBLIC_KEY")
        return jsonify({"error": "ImageKit not initialized", "debug": f"Public Key Present: {bool(pub)}"}), 500
    
    try:
        # Check if the SDK uses .list_files() or .files.list()
        try:
            files_res = ik.list_files({"path": "/"})
        except AttributeError:
            files_res = ik.files.list({"path": "/"})

        # Handle different response formats (Object vs List)
        files = getattr(files_res, 'list', files_res)
        
        reports_list = []
        for f in files:
            # SDK versions vary: some use dictionaries, some use objects
            f_dict = f if isinstance(f, dict) else f.__dict__
            
            tags = f_dict.get('tags', [])
            if tags:
                reports_list.append({
                    "id": f_dict.get('fileId') or f_dict.get('file_id'),
                    "title": tags[0],
                    "year": tags[1] if len(tags) > 1 else "2026",
                    "url": f_dict.get('url'),
                    "type": (f_dict.get('name') or "PDF").split('.')[-1].upper()
                })
        return jsonify(reports_list)
    except Exception as e:
        # THIS IS CRITICAL: It sends the actual error message to your screen
        return jsonify({"error": "Internal Crash", "details": str(e)}), 500

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