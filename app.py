from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os

# Initialize extensions first, before creating the app
db = SQLAlchemy()
migrate = Migrate()

# Create the Flask application
app = Flask(__name__, static_url_path='/static', static_folder='static')

# PostgreSQL configuration
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'postgresql://friepetre:friestyler@localhost:5432/qollabi_smart'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the application with extensions
db.init_app(app)
migrate.init_app(app, db)

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
@app.route('/admin')
def admin():
    try:
        # Pre-fetch the data for both sections
        degoudse_settings = DeGoudseSettings.query.order_by(DeGoudseSettings.section_number).all()
        baloise_settings = BaloiseSettings.query.order_by(BaloiseSettings.section_number).all()
        
        print("Pre-fetched De Goudse settings:", [s.to_dict() for s in degoudse_settings])
        print("Pre-fetched Baloise settings:", [s.to_dict() for s in baloise_settings])
        
        return render_template('admin.html')
    except Exception as e:
        print("Error in admin route:", str(e))
        return render_template('admin.html')

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

@app.route('/api/degoudse/settings', methods=['GET', 'POST'])
def degoudse_settings():
    if request.method == 'POST':
        try:
            data = request.json
            print("Received data:", data)  # Debug log
            
            setting = DeGoudseSettings.query.filter_by(section_number=data['section_number']).first()
            
            if setting:
                print("Updating existing setting")  # Debug log
                setting.title = data.get('title', setting.title)
                setting.link = data.get('link', setting.link)
                setting.content = data.get('content', setting.content)
            else:
                print("Creating new setting")  # Debug log
                setting = DeGoudseSettings(
                    section_number=data['section_number'],
                    title=data.get('title', ''),
                    link=data.get('link', ''),
                    content=data.get('content', '')
                )
                db.session.add(setting)
            
            db.session.commit()
            print("Settings saved successfully")  # Debug log
            return jsonify({"status": "success", "message": "Settings saved successfully"})
        except Exception as e:
            print("Error saving settings:", str(e))  # Debug log
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 