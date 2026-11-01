from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import Config
from database import close_db, init_db
from routes import locations, reports


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    init_db(app.config["DATABASE"], app.config["SEED_SAMPLE_DATA"])
    app.teardown_appcontext(close_db)

    app.register_blueprint(locations.bp, url_prefix="/api")
    app.register_blueprint(reports.bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # send errors back as JSON instead of Flask's HTML pages
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unexpected error")
        return jsonify(error="Internal server error"), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=Config.HOST, port=Config.PORT, debug=True)
