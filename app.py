from flask import Flask
from flask_cors import CORS
from config import Config
from routes.question_routes import question_bp
from routes.auth_routes import auth_bp
from models.models import init_db

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

# Initialize database
init_db()

# Register blueprints
app.register_blueprint(question_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')

if __name__ == '__main__':
    app.run(debug=True) 