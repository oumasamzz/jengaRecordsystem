import os
from flask import Flask, render_template, request, jsonify
from imagekitio import ImageKit

app = Flask(__name__, template_folder='../templates')

# Initialize ImageKit
imagekit = ImageKit(
    public_key=os.environ.get("IK_PUBLIC_KEY"),
    private_key=os.environ.get("IK_PRIVATE_KEY"),
    url_endpoint=os.environ.get("IK_URL_ENDPOINT")
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    try:
        # Fetch files from the /reports folder
        files = imagekit.list_files({
            "path": "/reports",
            "includeFolder": False
        })
        
        # Format the data for your UI
        # We store Title and Year in 'tags' for simplicity: ["Title", "2026"]
        reports_list = []
        for f in files:
            tags = f.tags if f.tags else ["Untitled", "N/A"]
            reports_list.append({
                "id": f.file_id,
                "title": tags[0],
                "year": tags[1] if len(tags) > 1 else "N/A",
                "url": f.url,
                "type": f.name.split('.')[-1]
            })
        return jsonify(reports_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')
        title = request.form.get('title')
        year = request.form.get('year')

        if not file:
            return jsonify({"error": "No file provided"}), 400

        # Upload to ImageKit
        # We store the Title and Year as Tags so we don't need a separate database!
        upload_res = imagekit.upload_file(
            file=file.read(),
            file_name=file.filename,
            options={
                "folder": "/reports",
                "tags": [title, year],
                "use_unique_file_name": True
            }
        )
        
        return jsonify({"success": True, "url": upload_res.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete/<file_id>', methods=['DELETE'])
def delete(file_id):
    if request.headers.get("X-Admin-Key") != "Tandy254./":
        return jsonify({"error": "Unauthorized"}), 403
    try:
        imagekit.delete_file(file_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500