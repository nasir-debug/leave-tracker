from flask import Flask, send_from_directory

from server import config
from server.db import init_db, bootstrap_admin
from server.routes import auth_routes, employee_routes, leave_routes, calendar_routes, settings_routes


def create_app():
    app = Flask(__name__, static_folder=None)
    init_db(app)
    bootstrap_admin()

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(employee_routes.bp)
    app.register_blueprint(leave_routes.bp)
    app.register_blueprint(calendar_routes.bp)
    app.register_blueprint(settings_routes.bp)

    @app.route("/")
    def index():
        return send_from_directory(config.STATIC_DIR, "index.html")

    @app.route("/<path:path>")
    def static_files(path):
        return send_from_directory(config.STATIC_DIR, path)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
