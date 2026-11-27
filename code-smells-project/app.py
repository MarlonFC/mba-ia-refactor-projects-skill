import logging

from flask import Flask
from flask_cors import CORS

from config.settings import Settings
from middlewares.error_handler import register_error_handlers
from models.database import init_db
from views.pedido_routes import pedido_bp
from views.produto_routes import produto_bp
from views.sistema_routes import sistema_bp
from views.usuario_routes import usuario_bp

logger = logging.getLogger(__name__)


def create_app(settings=Settings) -> Flask:
    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app, origins=app.config["CORS_ORIGINS"])
    init_db(app)
    register_error_handlers(app)
    for blueprint in (produto_bp, usuario_bp, pedido_bp, sistema_bp):
        app.register_blueprint(blueprint)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = create_app()
    logger.info("Servidor iniciado em http://%s:%s", Settings.HOST, Settings.PORT)
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
