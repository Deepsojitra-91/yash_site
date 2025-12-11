from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv
from extensions import mongo
from routes.admin_routes import admin_bp
from routes.user_routes import user_bp
from routes.image_routes import image_bp  

load_dotenv()
app = Flask(__name__)

CORS(app)

app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "change_this_secret_key")

# Register blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(image_bp)  # NEW BLUEPRINT

MAINTENANCE_MODE = False

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


@app.before_request
def show_maintenance():
    # Allow API access even in maintenance
    if MAINTENANCE_MODE and not request.path.startswith("/api/"):
        return render_template("maintenance.html"), 503
    
    
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)