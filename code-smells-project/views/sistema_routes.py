from flask import Blueprint, current_app, jsonify

from controllers import sistema_controller
from middlewares.auth import require_admin

sistema_bp = Blueprint("sistema", __name__)


@sistema_bp.get("/")
def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": current_app.config["VERSAO"],
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    })


@sistema_bp.get("/health")
def health_check():
    return jsonify(sistema_controller.health()), 200


@sistema_bp.post("/admin/reset-db")
@require_admin
def reset_database():
    sistema_controller.resetar_banco()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
