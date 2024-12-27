from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# PostgreSQL configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/qollabi_smart'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class DeGoudseSettings(db.Model):
    __tablename__ = 'degoudse_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    section_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    link = db.Column(db.String(500))
    content = db.Column(db.Text)  # For section 5
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
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
            'title': self.title,
            'link': self.link,
            'content': self.content
        }

# Routes for saving settings
@app.route('/save_degoudse_settings', methods=['POST'])
def save_degoudse_settings():
    data = request.json.get('degoudse', [])
    
    try:
        # Clear existing settings
        DeGoudseSettings.query.delete()
        
        # Save new settings
        for index, item in enumerate(data, 1):
            setting = DeGoudseSettings(
                section_number=index,
                title=item.get('title'),
                link=item.get('link'),
                content=item.get('content')
            )
            db.session.add(setting)
        
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_degoudse_settings')
def get_degoudse_settings():
    settings = DeGoudseSettings.query.order_by(DeGoudseSettings.section_number).all()
    return jsonify([setting.to_dict() for setting in settings])

@app.route('/save_baloise_settings', methods=['POST'])
def save_baloise_settings():
    data = request.json.get('baloise', [])
    
    try:
        # Clear existing settings
        BaloiseSettings.query.delete()
        
        # Save new settings
        for index, item in enumerate(data, 1):
            setting = BaloiseSettings(
                section_number=index,
                title=item.get('title'),
                link=item.get('link'),
                content=item.get('content')
            )
            db.session.add(setting)
        
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_baloise_settings')
def get_baloise_settings():
    settings = BaloiseSettings.query.order_by(BaloiseSettings.section_number).all()
    return jsonify([setting.to_dict() for setting in settings])

# Page routes
@app.route('/')
@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/degoudse')
def degoudse():
    return render_template('degoudse.html')

@app.route('/baloise')
def baloise():
    return render_template('baloise.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 