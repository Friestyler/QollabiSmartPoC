from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import openai
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Initialize extensions first, before creating the app
db = SQLAlchemy()
migrate = Migrate()

# Load environment variables from .env file
print("Starting application...")
print("Loading environment variables...")
load_dotenv()

# Access the API keys
openai.api_key = os.getenv('OPENAI_API_KEY')
pinecone_api_key = os.getenv('PINECONE_API_KEY')

# Check if the Pinecone API key is loaded
if not pinecone_api_key:
    raise ValueError("Pinecone API key is not set. Please check your .env file.")

# Add these debug prints
print("Initializing Pinecone...")
print(f"Pinecone API Key exists: {bool(pinecone_api_key)}")
try:
    pc = Pinecone(api_key=pinecone_api_key)
    print("Pinecone initialized successfully")
    print("Creating index...")
    index_name = 'quickstart'
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=2,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
    print("Index creation completed")
except Exception as e:
    print(f"Error initializing Pinecone: {str(e)}")

print("Pinecone API Key:", pinecone_api_key)

def create_app():
    app = Flask(__name__, static_url_path='/static', static_folder='static')

    # PostgreSQL configuration
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'postgresql://friepetre:friestyler@localhost:5432/qollabi_smart'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'

    # Initialize the application with extensions
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()  # This will create tables
        
    return app

app = create_app()

# Database Models
class DeGoudseSettings(db.Model):
    __tablename__ = 'degoudse_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    section_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    link = db.Column(db.String(500))
    content = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'section_number': self.section_number,
            'title': self.title,
            'link': self.link,
            'content': self.content
        }

class BaloiseSettings(db.Model):
    __tablename__ = 'baloise_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    section_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    link = db.Column(db.String(500))
    content = db.Column(db.Text)  # For section 5
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'section_number': self.section_number,
            'title': self.title,
            'link': self.link,
            'content': self.content
        }

# Routes for saving settings
@app.route('/save_degoudse_settings', methods=['POST'])
def save_degoudse_settings():
    try:
        data = request.json
        print("Received data:", data)  # Debug print
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'})

        section = int(data.get('section'))
        print(f"Processing section {section}")  # Debug print

        # Find or create setting
        setting = DeGoudseSettings.query.filter_by(section_number=section).first()
        if not setting:
            setting = DeGoudseSettings(section_number=section)
            db.session.add(setting)
            print(f"Created new setting for section {section}")  # Debug print
        
        # Update the fields
        if section == 5:
            setting.content = data.get('content', '')
            print(f"Updated content for section 5: {setting.content[:100]}...")  # Debug print
        else:
            setting.title = data.get('title', '')
            setting.link = data.get('link', '')
            print(f"Updated section {section} - Title: {setting.title}, Link: {setting.link}")  # Debug print
        
        db.session.commit()
        print(f"Successfully saved section {section}")  # Debug print
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print("Error saving settings:", str(e))
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/get_degoudse_settings')
def get_degoudse_settings():
    try:
        settings = DeGoudseSettings.query.order_by(DeGoudseSettings.section_number).all()
        print("Retrieved settings:", [s.to_dict() for s in settings])  # Debug print
        
        # Ensure we have 5 sections
        result = []
        for i in range(1, 6):
            setting = next((s for s in settings if s.section_number == i), None)
            if setting:
                result.append(setting.to_dict())
            else:
                result.append({
                    'section_number': i,
                    'title': '',
                    'link': '',
                    'content': ''
                })
        
        print("Sending result:", result)  # Debug print
        return jsonify(result)
    except Exception as e:
        print("Error getting settings:", str(e))
        return jsonify([])

@app.route('/save_baloise_settings', methods=['POST'])
def save_baloise_settings():
    try:
        data = request.json
        print("Received Baloise data:", data)  # Debug print
        
        section_number = data.get('section_number')
        if not section_number:
            raise ValueError("Missing section_number")

        # Find or create setting
        setting = BaloiseSettings.query.filter_by(section_number=section_number).first()
        if not setting:
            setting = BaloiseSettings(section_number=section_number)
            db.session.add(setting)
            print(f"Created new Baloise setting for section {section_number}")

        # Update fields based on section type
        if section_number == 5:
            setting.content = data.get('content', '')
            setting.title = None
            setting.link = None
            print(f"Updated Baloise section 5 content: {setting.content[:100]}...")
        else:
            setting.title = data.get('title', '')
            setting.link = data.get('link', '')
            setting.content = None
            print(f"Updated Baloise section {section_number} - Title: {setting.title}, Link: {setting.link}")

        setting.updated_at = datetime.utcnow()
        db.session.commit()
        print(f"Successfully saved Baloise section {section_number}")

        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error saving Baloise settings: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_baloise_settings')
def get_baloise_settings():
    try:
        settings = BaloiseSettings.query.order_by(BaloiseSettings.section_number).all()
        result = []
        
        # Ensure we have 5 sections, even if some are empty
        for i in range(1, 6):
            setting = next((s for s in settings if s.section_number == i), None)
            if setting:
                result.append({
                    'section_number': i,
                    'title': setting.title,
                    'link': setting.link,
                    'content': setting.content
                })
            else:
                result.append({
                    'section_number': i,
                    'title': '',
                    'link': '',
                    'content': ''
                })
        
        print("Sending Baloise settings:", result)  # Debug log
        return jsonify(result)
    except Exception as e:
        print("Error getting Baloise settings:", str(e))
        return jsonify([])

# Page routes
@app.route('/')
def measure():
    return render_template('measure.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/manage')
def manage():
    return render_template('manage.html', openai_key=os.getenv('OPENAI_API_KEY'), pinecone_key=os.getenv('PINECONE_API_KEY'))

@app.route('/degoudse')
def degoudse():
    try:
        settings = DeGoudseSettings.query.order_by(DeGoudseSettings.section_number).all()
        print("Rendering De Goudse page with settings:", [s.to_dict() for s in settings])
        return render_template('degoudse.html')
    except Exception as e:
        print("Error in degoudse route:", str(e))
        return render_template('degoudse.html')

@app.route('/baloise')
def baloise():
    try:
        settings = BaloiseSettings.query.order_by(BaloiseSettings.section_number).all()
        print("Rendering Baloise page with settings:", [s.to_dict() for s in settings])
        return render_template('baloise.html')
    except Exception as e:
        print("Error in baloise route:", str(e))
        return render_template('baloise.html')

@app.route('/navigation')
def navigation():
    return render_template('navigation.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        # Process the file and update the vector database
        process_file(file.filename)
        return redirect(url_for('manage'))

def process_file(filename):
    # Implement logic to process the file and update the vector database
    pass

@app.route('/update_settings', methods=['POST'])
def update_settings():
    openai_key = request.form.get('openai_key')
    pinecone_key = request.form.get('pinecone_key')
    # Update environment variables or configuration as needed
    # For example, you might save these to a database or a secure storage
    return redirect(url_for('manage'))

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    query = data.get('query')
    response = generate_response(query)
    return jsonify({'response': response})

def generate_response(query):
    # Retrieve relevant documents from the vector database
    relevant_docs = retrieve_documents(query)
    
    # Use OpenAI to generate a response using the chat model
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Use the chat model
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query}
        ],
        max_tokens=150
    )
    return response.choices[0].message['content'].strip()

def retrieve_documents(query):
    # Implement logic to retrieve documents from the vector database
    return []

if __name__ == '__main__':
    app.run(debug=True) 