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
import threading
from werkzeug.utils import secure_filename
import tempfile
import textwrap
import PyPDF2

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

# At the top of your file, add a flag to prevent multiple initializations
initialization_lock = threading.Lock()
initialization_done = False

# Add this near the top of your file with other configurations
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx', 'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Replace the initialization code
try:
    with initialization_lock:
        if not initialization_done:
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
            index_name = os.getenv('PINECONE_INDEX_NAME')
            
            # Check if index exists but DON'T try to delete it
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
                logger.info("Index created successfully")
            else:
                logger.info(f"Using existing index: {index_name}")
            
            initialization_done = True

except Exception as e:
    logger.error(f"Error during initialization: {str(e)}")
    raise

# Remove any logging of API keys
logger.info("Initializing application...")
logger.info(f"S3 Bucket Name: {os.getenv('S3_BUCKET_NAME')}")
logger.info(f"Pinecone Index Name: {os.getenv('PINECONE_INDEX_NAME')}")

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
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='us-east-1'  # or your preferred region
)

def upload_file_to_s3(file_data, filename):
    try:
        bucket_name = os.getenv('S3_BUCKET_NAME')
        logger.info(f"Uploading {filename} to S3 bucket {bucket_name}")
        s3_client.upload_fileobj(
            file_data,
            bucket_name,
            filename
        )
        return True
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        return False

def get_documents_from_s3():
    try:
        bucket_name = os.getenv('S3_BUCKET_NAME')
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        documents = []
        if 'Contents' in response:
            for obj in response['Contents']:
                documents.append({
                    'filename': obj['Key'],
                    'upload_date': obj['LastModified'].isoformat()
                })
        return documents
    except Exception as e:
        logger.error(f"Error listing S3 objects: {str(e)}")
        return []

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
    return render_template('measure.html', 
                         current_page='measure',
                         demo_settings=demo_settings)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/manage')
def manage():
    demo_settings = DemoSettings.query.order_by(DemoSettings.section_number).all()
    return render_template('manage.html', 
                         current_page='manage',
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
    try:
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'success': False, 'message': 'No file part'})
        
        file = request.files['file']
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'success': False, 'message': 'No selected file'})
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            logger.info(f"Processing file: {filename}")
            
            # Upload to S3
            logger.info(f"Starting S3 upload for {filename}")
            if not upload_file_to_s3(file, filename):
                logger.error("Failed to upload to S3")
                return jsonify({'success': False, 'message': 'Failed to upload to S3'})
            
            logger.info("S3 upload successful")
            
            # Process for Pinecone
            logger.info("Starting Pinecone processing")
            try:
                # Get the file from S3
                s3_client = boto3.client('s3')
                bucket_name = os.getenv('S3_BUCKET_NAME')
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    logger.info(f"Downloading from S3: {filename}")
                    s3_client.download_fileobj(bucket_name, filename, temp_file)
                    temp_file.seek(0)
                    
                    logger.info("Creating PDF reader")
                    pdf_reader = PyPDF2.PdfReader(temp_file.name)
                    text_chunks = []
                    
                    logger.info("Extracting text from PDF")
                    for page_num, page in enumerate(pdf_reader.pages):
                        text = page.extract_text()
                        chunks = textwrap.wrap(text, 1000)
                        text_chunks.extend(chunks)
                        logger.info(f"Processed page {page_num + 1}, got {len(chunks)} chunks")
                    
                    logger.info(f"Total chunks to process: {len(text_chunks)}")
                    
                    # Initialize Pinecone
                    logger.info("Initializing Pinecone")
                    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
                    index = pc.Index(os.getenv('PINECONE_INDEX_NAME'))
                    
                    # Create embeddings and upload to Pinecone
                    for i, chunk in enumerate(text_chunks):
                        logger.info(f"Processing chunk {i + 1}/{len(text_chunks)}")
                        embedding = get_embedding(chunk)
                        
                        # Upload to Pinecone
                        index.upsert(
                            vectors=[{
                                'id': f"{filename}-chunk-{i}",
                                'values': embedding,
                                'metadata': {
                                    'text': chunk,
                                    'filename': filename
                                }
                            }]
                        )
                        logger.info(f"Uploaded chunk {i + 1} to Pinecone")
                    
                    os.unlink(temp_file.name)
                    logger.info("File processing completed successfully")
                    return jsonify({'success': True, 'message': 'File uploaded and processed successfully'})
                    
            except Exception as e:
                logger.error(f"Error processing file for Pinecone: {str(e)}")
                return jsonify({'success': False, 'message': f'Failed to process file: {str(e)}'})
                
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

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
        index = pc.Index(os.getenv('PINECONE_INDEX_NAME'))
        
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
            if hasattr(match, 'score') and match.score > 0.7:
                if hasattr(match, 'metadata') and 'text' in match.metadata:
                    contexts.append(match.metadata['text'])

        # Prepare the context string
        context_text = "\n".join(contexts) if contexts else ""
        
        # Prepare the messages for GPT with structured format
        messages = [
            {"role": "system", "content": """You are a helpful assistant. Structure your responses clearly with sections and bullet points.
            Use the following format:
            
            ## Summary
            Brief overview of the answer
            
            ### Key Points
            * Important point 1
            * Important point 2
            * Important point 3
            
            ### Details
            Detailed explanation with relevant information
            
            ### References
            * Reference relevant documents or sections if available"""}
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
        logger.info(f"Final response: {response_text[:200]}...")

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

@app.route('/get_documents', methods=['GET'])
def get_documents():
    try:
        documents = get_documents_from_s3()
        return jsonify(documents)
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_document/<filename>', methods=['DELETE'])
def delete_document(filename):
    try:
        logger.info(f"Attempting to delete document: {filename}")
        
        # Delete from S3
        try:
            s3_client = boto3.client('s3')
            s3_client.delete_object(
                Bucket=os.getenv('S3_BUCKET_NAME'),
                Key=filename
            )
            logger.info(f"Deleted {filename} from S3")
        except Exception as e:
            logger.error(f"Error deleting from S3: {str(e)}")
            return jsonify({'success': False, 'message': f'Failed to delete from S3: {str(e)}'}), 500

        # Delete from Pinecone
        try:
            pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
            index = pc.Index(os.getenv('PINECONE_INDEX_NAME'))
            
            # Delete all chunks for this file
            # First, get all vector IDs that start with the filename
            vector_ids = [f"{filename}-chunk-{i}" for i in range(1000)]  # Adjust range as needed
            
            # Delete vectors in batches
            batch_size = 100
            for i in range(0, len(vector_ids), batch_size):
                batch = vector_ids[i:i + batch_size]
                try:
                    index.delete(ids=batch)
                except Exception as e:
                    logger.warning(f"Error deleting batch from Pinecone: {str(e)}")
                    
            logger.info(f"Deleted vectors for {filename} from Pinecone")
        except Exception as e:
            logger.error(f"Error deleting from Pinecone: {str(e)}")
            return jsonify({'success': False, 'message': f'Failed to delete from Pinecone: {str(e)}'}), 500

        return jsonify({'success': True, 'message': 'Document deleted successfully'})
        
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/reset_database', methods=['POST'])
def reset_database():
    try:
        # Clear S3
        logger.info("Clearing S3 bucket...")
        bucket_name = os.getenv('S3_BUCKET_NAME')
        s3_client = boto3.client('s3')
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in objects:
            for obj in objects['Contents']:
                s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                logger.info(f"Deleted {obj['Key']} from S3")
        
        # Clear Pinecone
        logger.info("Clearing Pinecone index...")
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index_name = os.getenv('PINECONE_INDEX_NAME')
        
        try:
            index = pc.Index(index_name)
            index.delete(delete_all=True)
            logger.info("Pinecone index cleared")
        except Exception as e:
            logger.warning(f"Error clearing Pinecone index: {str(e)}")
            # If the error is about namespace not found, we can ignore it
            if "Namespace not found" not in str(e):
                raise
        
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

def get_embedding(text):
    client = OpenAI()
    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

if __name__ == '__main__':
    app.run(debug=True) 