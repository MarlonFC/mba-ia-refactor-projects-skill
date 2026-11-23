from flask import Blueprint, jsonify, request

from config.settings import API_VERSION
from controllers import sistema_controller
from middlewares.auth import require_admin

sistema_bp = Blueprint("sistema", __name__)


@sistema_bp.get("/")
def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": API_VERSION,
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


@sistema_bp.post("/admin/query")
@require_admin
def executar_query():
    linhas = sistema_controller.executar_query(request.get_json(silent=True))
    if linhas is None:
        return jsonify({"mensagem": "Query executada", "sucesso": True}), 200
    return jsonify({"dados": linhas, "sucesso": True}), 200
