import logging

from controllers.validation import require_json
from middlewares.error_handler import AppError, NotFoundError, ValidationError
from models import usuario_model

logger = logging.getLogger(__name__)


def listar() -> list[dict]:
    return usuario_model.listar()


def buscar(usuario_id: int) -> dict:
    usuario = usuario_model.buscar_por_id(usuario_id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar(dados) -> int:
    dados = require_json(dados)
    nome, email, senha = dados.get("nome", ""), dados.get("email", ""), dados.get("senha", "")
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(valor, str) for valor in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser texto")

    usuario_id = usuario_model.criar(nome, email, senha)
    logger.info("Usuário criado: id=%s", usuario_id)
    return usuario_id


def login(dados) -> dict:
    dados = dados if isinstance(dados, dict) else {}
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    if not isinstance(email, str) or not isinstance(senha, str):
        raise ValidationError("Email e senha devem ser texto")

    usuario = usuario_model.autenticar(email, senha)
    if not usuario:
        logger.warning("Login falhou")
        raise AppError(401, "Email ou senha inválidos", sucesso=False)
    logger.info("Login bem-sucedido: id=%s", usuario["id"])
    return usuario
