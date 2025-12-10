from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
from extensions import mongo
from routes.admin_routes import admin_bp
from routes.user_routes import user_bp

load_dotenv()
app = Flask(__name__)

CORS(app)

app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "change_this_secret_key")

app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)


@app.route('/health')
def health_check():
    try:
        mongo.db.command('ping')
        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"detail": "Bad request"}), 400


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({"detail": "API endpoint not found"}), 404
    return jsonify({"detail": "Page not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"detail": "Internal server error"}), 500
