from flask import * #importing flask (Install it using python -m pip install flask)
from werkzeug.utils import secure_filename
import os
from prompts import get_default
import markdown2
from flask_login import login_user
from pdfid.pdfid import PDFiD
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
import xml.etree.ElementTree as ET
from azurecloud import AzureBlobStorageManager

# Create the LoginManager instance
login_manager = LoginManager()



def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    login_manager.init_app(app)  # Initialize it for your application
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    return app



def is_pdf_safe(file):
    """Run PDFiD on the PDF and check the output for signs of exploits."""
    xmlcontent = PDFiD(file)

    # Parse the XML content into an ElementTree
    root = ET.fromstring(xmlcontent.toxml())

    # Search for 'JS' and 'JavaScript' tags
    js_elements = root.findall('.//JS')
    javascript_elements = root.findall('.//JavaScript')

    # Then check counts
    if len(js_elements) > 0 or len(javascript_elements) > 0:
        return False

    return True



app = create_app()
app.config['UPLOAD_FOLDER'] = 'UPLOAD_FOLDER'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['TEXT_FOLDER'] = 'TEXT_FOLDER'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:////tmp/695ece9dd1a749c2a94ddeea02d1fce3.db'  # replace with your DB URI
app.config['PASSWORD']='automatednotes'
app.config['JSON_FOLDER'] = './jobs'

db = SQLAlchemy(app)




# Update your User model to inherit from UserMixin, which includes required methods
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    filenames = db.relationship('Filename', backref='user', lazy=True)

class Filename(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


def filename_to_blobname(filename):
    return filename +'.ext'


with app.app_context():
    db.create_all()
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
            user = User.query.filter_by(name=usr).first()
            if not user:
                user = User(name=usr)
                db.session.add(user)
                db.session.commit()

            login_user(user, remember=True)
            # further processing...
        else:
            flash('Invalid username or password')
            return redirect(request.url)
        startIndex = int(request.form.get("spinBox1", 0))
        # Check if a file was uploaded
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
                db_filename = Filename(name=filename, user_id=user.id)
                db.session.add(db_filename)
                db.session.commit()

                # if not is_pdf_safe(file.name):
                #     flash('Potentially unsafe file blocked')
                #     return redirect(request.url)
                filenames.append(filename)
            else: 
                filenames.append("<File Not Defined>")
    q=User.query.filter_by(name=usr).first()
    if q:
        return render_template('account.html', username=usr, filenames=[f.name for f in q.filenames if f])
    else:
        return render_template('account.html', username=usr, filenames=[])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']




def runAPP(): #checking if __name__'s value is '__main__'. __name__ is an python environment variable who's value will always be '__main__' till this is the first instatnce of app.py running
    app.run(debug=False,port=8000) #running flask (Initalised on line 4)





if __name__ == "__main__":
    runAPP()