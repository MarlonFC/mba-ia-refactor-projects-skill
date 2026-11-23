"""Casos de uso de Usuário e autenticação."""
import logging

from controllers.validation import exigir_objeto, textos_preenchidos
from middlewares.error_handler import AppError, NotFoundError, ValidationError
from models import usuario_model

logger = logging.getLogger(__name__)


def listar() -> list[dict]:
    return usuario_model.listar()


def obter(usuario_id: int) -> dict:
    usuario = usuario_model.buscar_por_id(usuario_id)
    if usuario is None:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar(dados) -> int:
    dados = exigir_objeto(dados)
    nome, email, senha = dados.get("nome", ""), dados.get("email", ""), dados.get("senha", "")
    if not textos_preenchidos(nome, email, senha):
        raise ValidationError("Nome, email e senha são obrigatórios")
    usuario_id = usuario_model.criar(nome, email, senha)
    logger.info("Usuário criado com ID %s", usuario_id)
    return usuario_id


def login(dados) -> dict:
    dados = exigir_objeto(dados, aceita_vazio=True)
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not textos_preenchidos(email, senha):
        raise ValidationError("Email e senha são obrigatórios")
    usuario = usuario_model.autenticar(email, senha)
    if usuario is None:
        logger.info("Falha de login")
        raise AppError(401, "Email ou senha inválidos", sucesso=False)
    logger.info("Login bem-sucedido do usuário %s", usuario["id"])
    return usuario
