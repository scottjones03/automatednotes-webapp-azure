from flask import (Flask, render_template, request, flash, redirect)
from werkzeug.utils import secure_filename
import os
import json
from prompts import get_default
from flask_login import login_user
from flask_login import LoginManager, UserMixin
from azurecloud import AzureBlobStorageManager
from azure.storage.blob import BlobServiceClient
import markdown2

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    @property
    def is_active(self):
        # Here you should write whatever the code is
        # that checks the database if your user is active
        return True


# Create the LoginManager instance
login_manager = LoginManager()

# Create the BlobServiceClient object which will be used to create a container client
blob_service_client = BlobServiceClient(AzureBlobStorageManager.URL,AzureBlobStorageManager.CREDENTIALS)

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    login_manager.init_app(app)  # Initialize it for your application
    return app

@login_manager.user_loader
def load_user(user_id):
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
    except Exception:
        return None
    if user_id in users:
        return User(user_id)
    return None

app = create_app()
app.config['UPLOAD_FOLDER'] = 'UPLOAD_FOLDER'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['TEXT_FOLDER'] = 'TEXT_FOLDER'
app.config['PASSWORD']='automatednotes'
app.config['JSON_FOLDER'] = './jobs'

def filename_to_blobname(filename):
    return filename +'.ext'

@app.route("/view_file/<filename>", methods=["GET"])
def view_file(filename):
    p=AzureBlobStorageManager.download_response(filename)
    with open(p, 'r') as file:
        file_content = file.read()
    html_content = markdown2.markdown(file_content)  # convert Markdown to HTML
    return render_template('view_file.html', filename=filename, file_content=html_content)

@app.route("/") #defining the routes for the home() funtion (Multiple routes can be used as seen here)
@app.route("/home", methods=["POST", "GET"])
def home():
    return render_template("home.html") #rendering our home.html contained within /templates

@app.route("/account", methods=["POST", "GET"])
def account():
    usr = "<User Not Defined>"
    filenames = []
    startIndex =0
    if request.method == "POST":
        usr = request.form.get("name", "<User Not Defined>")
        password = request.form.get("password")
        fileprefix = request.form.get("fileprefix", "")
        selected_model = request.form.get("modelSelect", "3")
        topic = request.form.get("topic", "computer science")
        content = request.form.get("content", "code snippets, examples, algorithms, or pseudocode")
        revision_questions = request.form.get("questions", "3")
        prompts = []
        prompt = request.form.get("prompt", "")
        if prompt:
            prompts.append(prompt)
        if request.form.get("with_default", "y")=="y":
            prompts.append(get_default(topic, content, revision_questions))
        if password==app.config["PASSWORD"]: 
            user = load_user(usr)
            if not user:
                try:
                    with open('users.json', 'r') as f:
                        users = dict(json.load(f))
                except Exception:
                    users = {}
                users[usr] = {'id': usr, 'files': []}
                with open('users.json', 'w') as f:
                    json.dump(users, f)
                user = load_user(usr)
            login_user(user, remember=True)

        else:
            flash('Invalid username or password')
            return redirect(request.url)
        startIndex = int(request.form.get("spinBox1", 0))
        if 'pdfFile' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)

        files = request.files.getlist('pdfFile')

        for file in files:
            if file and allowed_file(file.filename):
                file.filename = fileprefix+file.filename
                filename = secure_filename(usr+'--'+file.filename)
                blob_name = filename_to_blobname(filename)
                blob_name_job = filename_to_blobname('TODO--'+filename)
                AzureBlobStorageManager.upload_file(blob_name=blob_name, data=file)
                AzureBlobStorageManager.upload_file(blob_name=blob_name_job, data=str([filename, blob_name, startIndex, usr, selected_model, prompts]))

                with open('users.json', 'r') as f:
                    users = json.load(f)
                if 'files' in users[usr]:
                    users[usr]['files'].append(filename)
                else:
                    users[usr]['files'] = [filename]
                with open('users.json', 'w') as f:
                    json.dump(users, f)

                filenames.append(filename)
            else: 
                filenames.append("<File Not Defined>")
    with open('users.json', 'r') as f:
        users = json.load(f)
    user_filenames = users[usr].get('files', [])
    return render_template('account.html', username=usr, filenames=user_filenames)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def runAPP():
    app.run(debug=True, port=4949, host='0.0.0.0')

if __name__ == "__main__":
    runAPP()
