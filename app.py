from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import openai
from dotenv import load_dotenv
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import logging
from PyPDF2 import PdfReader
from openai import OpenAI
import time
import boto3
from botocore.exceptions import ClientError

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

# Add these debug prints at the start of your app
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add these debug prints right after your imports
logger.info("Starting application initialization...")

def init_pinecone():
    try:
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        # Get index name from environment variable
        index_name = os.getenv('PINECONE_INDEX_NAME')  # Remove 'quickstart' default
        logger.info(f"Initializing Pinecone with index: {index_name}")
        
        # Check if index exists
        existing_indexes = pc.list_indexes().names()
        
        if index_name not in existing_indexes:
            logger.info(f"Creating new index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=1536,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            # Wait for index to be ready
            import time
            time.sleep(10)  # Give the index time to initialize
            
        # Verify index is ready
        index = pc.Index(index_name)
        # Test the connection
        try:
            index.describe_index_stats()
            logger.info("Index is ready")
        except Exception as e:
            logger.error(f"Index not ready: {str(e)}")
            raise
            
        return index
    except Exception as e:
        logger.error(f"Error initializing Pinecone: {str(e)}")
        raise

# Remove any logging of API keys
logger.info("Initializing application...")
logger.info(f"S3 Bucket Name: {os.getenv('S3_BUCKET_NAME')}")
logger.info(f"Pinecone Index Name: {os.getenv('PINECONE_INDEX_NAME', 'quickstart')}")

try:
    logger.info("Loading environment variables...")
    load_dotenv()
    
    logger.info("Checking Pinecone API key...")
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    if not pinecone_api_key:
        logger.error("Pinecone API key not found in environment variables")
        raise ValueError("Pinecone API key is not set")
    
    logger.info("Initializing Pinecone...")
    pc = Pinecone(api_key=pinecone_api_key)
    logger.info("Pinecone initialized successfully")
    
    logger.info("Setting up Pinecone index...")
    index_name = os.getenv('PINECONE_INDEX_NAME')  # Remove hardcoded 'quickstart'
    if index_name in pc.list_indexes().names():
        logger.info(f"Deleting existing index: {index_name}")
        pc.delete_index(index_name)
        
    logger.info(f"Creating new index: {index_name}")
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric='cosine',
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )
    logger.info("Index created successfully")
except Exception as e:
    logger.error(f"Error during initialization: {str(e)}")
    raise

print("Pinecone API Key:", pinecone_api_key)

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key-here')

# Use Heroku's DATABASE_URL environment variable if available, otherwise use local database
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    # Heroku's postgres:// needs to be updated to postgresql://
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'postgresql://localhost/smart'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

# Initialize the application with extensions
db.init_app(app)
migrate.init_app(app, db)

with app.app_context():
    db.create_all()  # This will create tables
    

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

class DemoSettings(db.Model):
    __tablename__ = 'demo_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    section_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    link = db.Column(db.String(500))
    content = db.Column(db.Text)  # For section 5
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DemoSettings {self.section_number}: {self.title}>'

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

def upload_to_s3(file_path, filename):
    """Upload a file to S3"""
    try:
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if not bucket_name:
            logger.error("S3_BUCKET_NAME not set in environment variables")
            return False
            
        if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
            logger.error("AWS credentials not set in environment variables")
            return False

        logger.info(f"Attempting to upload {filename} to S3 bucket: {bucket_name}")
        s3_client.upload_file(
            file_path, 
            bucket_name, 
            filename
        )
        logger.info(f"Successfully uploaded {filename} to S3")
        return True
    except ClientError as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {str(e)}")
        return False

def download_from_s3(filename):
    """Download a file from S3"""
    try:
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        s3_client.download_file(
            os.getenv('S3_BUCKET_NAME'),
            filename,
            local_path
        )
        return True
    except ClientError as e:
        logger.error(f"Error downloading from S3: {str(e)}")
        return False

def delete_from_s3(filename):
    """Delete a file from S3"""
    try:
        s3_client.delete_object(
            Bucket=os.getenv('S3_BUCKET_NAME'),
            Key=filename
        )
        return True
    except ClientError as e:
        logger.error(f"Error deleting from S3: {str(e)}")
        return False

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
    # Get all demo settings ordered by section number
    demo_settings = DemoSettings.query.order_by(DemoSettings.section_number).all()
    return render_template('measure.html', demo_settings=demo_settings)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/manage')
def manage():
    # Get all demo settings ordered by section number
    demo_settings = DemoSettings.query.order_by(DemoSettings.section_number).all()
    return render_template('manage.html', 
                         demo_settings=demo_settings,
                         openai_key=os.getenv('OPENAI_API_KEY'),
                         pinecone_key=os.getenv('PINECONE_API_KEY'))

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
        return jsonify({'success': False, 'message': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})
    
    if file and file.filename.endswith('.pdf'):
        try:
            logger.info(f"Starting upload process for {file.filename}")
            
            # Create uploads directory if it doesn't exist
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            logger.info(f"Saved file locally to {file_path}")
            
            # Upload to S3
            if upload_to_s3(file_path, filename):
                logger.info("Starting document processing...")
                if process_file(filename):
                    logger.info("Document successfully processed")
                    return jsonify({
                        'success': True, 
                        'message': 'File successfully uploaded to S3 and processed',
                        'location': 'S3'
                    })
                else:
                    logger.error("Failed to process document")
            else:
                logger.error("Failed to upload to S3")
            
            return jsonify({'success': False, 'message': 'Error processing file'})
                
        except Exception as e:
            logger.error(f"Error in upload: {str(e)}")
            return jsonify({'success': False, 'message': 'Error uploading file: ' + str(e)})
    else:
        return jsonify({'success': False, 'message': 'Only PDF files are allowed'})

def process_file(filename):
    try:
        logger.info(f"Processing file: {filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Read the PDF file
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        
        logger.info(f"Extracted text length: {len(text)}")
        
        # Split text into smaller chunks
        chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
        logger.info(f"Created {len(chunks)} chunks")
        
        # Initialize Pinecone
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        
        # Create or get index
        index_name = os.getenv('PINECONE_INDEX_NAME')  # Use environment variable
        try:
            index = pc.Index(index_name)
            logger.info("Using existing index")
        except Exception:
            logger.info(f"Creating new index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            time.sleep(5)  # Wait for index to be ready
            index = pc.Index(index_name)
        
        # Get embeddings using OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        records = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            response = client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002"
            )
            embedding = response.data[0].embedding
            
            records.append({
                "id": f"{filename}-chunk-{i}",
                "values": embedding,
                "metadata": {"text": chunk, "source": filename}
            })
        
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            logger.info(f"Upserting batch {i//batch_size + 1}")
            index.upsert(
                vectors=batch
            )
        
        logger.info("File processing complete")
        return True
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return False

@app.route('/update_settings', methods=['POST'])
def update_settings():
    openai_key = request.form.get('openai_key')
    pinecone_key = request.form.get('pinecone_key')
    # Update environment variables or configuration as needed
    # For example, you might save these to a database or a secure storage
    return redirect(url_for('manage'))

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message', '')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        logger.info(f"Received user message: {user_message}")

        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        logger.info("OpenAI client initialized")
        
        # Get embedding for the user's question
        logger.info("Getting embedding for user question...")
        embedding_response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=user_message
        )
        question_embedding = embedding_response.data[0].embedding
        logger.info("Embedding created successfully")

        # Query Pinecone
        logger.info("Initializing Pinecone...")
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index = pc.Index(os.getenv('PINECONE_INDEX_NAME'))  # Use environment variable
        
        # Search for relevant context
        logger.info("Querying Pinecone index...")
        query_response = index.query(
            vector=question_embedding,
            top_k=3,
            include_metadata=True
        )
        logger.info(f"Pinecone query response: {query_response}")

        # Extract relevant context from the matches
        contexts = []
        for match in query_response.matches:
            logger.info(f"Processing match with score: {match.score if hasattr(match, 'score') else 'no score'}")
            if hasattr(match, 'score') and match.score > 0.7:  # Only use relevant matches
                if hasattr(match, 'metadata') and 'text' in match.metadata:
                    contexts.append(match.metadata['text'])
                    logger.info(f"Added context from match: {match.metadata['text'][:100]}...")

        # Prepare the context string
        context_text = "\n".join(contexts) if contexts else ""
        logger.info(f"Final context length: {len(context_text)} characters")
        logger.info(f"Context used: {context_text[:200]}...")  # Log first 200 chars of context

        # Prepare the messages for GPT
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Use the provided context to answer questions, and if you're not sure about something, say so."}
        ]

        if context_text:
            prompt = f"Using this context:\n\n{context_text}\n\nPlease answer this question: {user_message}"
            logger.info(f"Using context in prompt. Prompt length: {len(prompt)}")
        else:
            prompt = f"Please answer this question: {user_message}\n\nNote: If you need specific information from documents to answer this question, please let me know."
            logger.info("No context available for this query")

        messages.append({"role": "user", "content": prompt})

        # Get response from GPT
        logger.info("Sending request to GPT...")
        chat_response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        logger.info("Received response from GPT")

        response_text = chat_response.choices[0].message.content
        logger.info(f"Final response: {response_text[:200]}...")  # Log first 200 chars of response

        return jsonify({
            'response': response_text,
            'context_used': bool(contexts),
            'debug_info': {
                'contexts_found': len(contexts),
                'context_length': len(context_text) if context_text else 0
            }
        })

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

def retrieve_documents(query):
    # Implement logic to retrieve documents from the vector database
    return []

@app.route('/update_demo_settings', methods=['POST'])
def update_demo_settings():
    try:
        # Create new demo settings
        demo_setting = DemoSettings(
            section_number=request.form.get('section_number'),
            title=request.form.get('title'),
            link=request.form.get('link'),
            content=request.form.get('content')
        )
        db.session.add(demo_setting)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/edit_demo_setting/<int:setting_id>', methods=['POST'])
def edit_demo_setting(setting_id):
    try:
        setting = DemoSettings.query.get_or_404(setting_id)
        setting.section_number = request.form.get('section_number')
        setting.title = request.form.get('title')
        setting.link = request.form.get('link')
        setting.content = request.form.get('content')
        db.session.commit()
        return jsonify({'success': True, 'message': 'Setting updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_demo_setting/<int:setting_id>', methods=['POST'])
def delete_demo_setting(setting_id):
    try:
        setting = DemoSettings.query.get_or_404(setting_id)
        db.session.delete(setting)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/get_demo_settings')
def get_demo_settings():
    try:
        settings = DemoSettings.query.order_by(DemoSettings.section_number).all()
        return jsonify([{
            'id': s.id,
            'section_number': s.section_number,
            'title': s.title,
            'link': s.link,
            'content': s.content,
            'updated_at': s.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        } for s in settings])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_documents')
def get_documents():
    try:
        documents = set()
        
        # Get local files
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                if filename.endswith('.pdf'):
                    documents.add(filename)
        
        # Get files from Pinecone
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index = pc.Index('quickstart')
        
        # Query for all vectors and get unique filenames from metadata
        results = index.query(
            vector=[0] * 1536,  # Dummy vector to get all documents
            top_k=10000,
            include_metadata=True
        )
        
        # Add filenames from Pinecone metadata
        for match in results.matches:
            if 'source' in match.metadata:
                documents.add(match.metadata['source'])
        
        # Convert to list of dictionaries with file info
        document_list = []
        for filename in documents:
            file_path = os.path.join(upload_folder, filename)
            document_list.append({
                'filename': filename,
                'upload_date': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat() if os.path.exists(file_path) else 'Unknown',
                'stored_in_pinecone': True
            })
        
        return jsonify(document_list)
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_document/<filename>', methods=['DELETE'])
def delete_document(filename):
    try:
        # Delete from filesystem
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from S3
        delete_from_s3(filename)
        
        # Delete from Pinecone
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index = pc.Index('quickstart')
        index.delete(filter={"source": filename})
        
        return jsonify({'success': True, 'message': 'Document deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/reset_database', methods=['POST'])
def reset_database():
    try:
        # Clear uploads folder
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        # Reset Pinecone index
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index_name = "quickstart"
        
        # Delete existing index if it exists
        if index_name in pc.list_indexes().names():
            pc.delete_index(index_name)
            
        # Create new index
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        
        return jsonify({'success': True, 'message': 'Database reset successfully'})
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Add a route to check S3 storage
@app.route('/check_s3', methods=['GET'])
def check_s3():
    try:
        # List objects in S3 bucket
        response = s3_client.list_objects_v2(
            Bucket=os.getenv('S3_BUCKET_NAME')
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'filename': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
        
        return jsonify({
            'success': True,
            'bucket': os.getenv('S3_BUCKET_NAME'),
            'files': files
        })
    except Exception as e:
        logger.error(f"Error checking S3: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Add this debug logging at app startup
logger.info(f"S3 Bucket Name: {os.getenv('S3_BUCKET_NAME')}")
logger.info(f"AWS Access Key ID exists: {bool(os.getenv('AWS_ACCESS_KEY_ID'))}")
logger.info(f"AWS Secret Access Key exists: {bool(os.getenv('AWS_SECRET_ACCESS_KEY'))}")

@app.route('/check_s3_connection', methods=['GET'])
def check_s3_connection():
    try:
        bucket_name = os.getenv('S3_BUCKET_NAME')
        logger.info(f"Checking S3 connection for bucket: {bucket_name}")
        
        # Try to list objects in the bucket
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            MaxKeys=1  # Just check for one object to verify access
        )
        
        return jsonify({
            'success': True,
            'bucket_name': bucket_name,
            'can_access': True,
            'response': {
                'has_contents': 'Contents' in response,
                'count': len(response.get('Contents', []))
            }
        })
    except ClientError as e:
        logger.error(f"Error accessing S3: {str(e)}")
        return jsonify({
            'success': False,
            'bucket_name': bucket_name,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True) 