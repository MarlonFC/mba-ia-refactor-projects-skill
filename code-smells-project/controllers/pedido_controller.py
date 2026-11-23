"""Casos de uso de Pedido e relatório de vendas."""
import logging

from config.settings import STATUS_PEDIDO_VALIDOS
from controllers.validation import como_inteiro, eh_numero, exigir_objeto
from middlewares.error_handler import ValidationError
from models import pedido_model
from services import notification_service

logger = logging.getLogger(__name__)


def _validar_itens(itens) -> list[dict]:
    if not isinstance(itens, list):
        raise ValidationError("Itens inválidos")
    validados = []
    for item in itens:
        produto_id = como_inteiro(item.get("produto_id")) if isinstance(item, dict) else None
        quantidade = item.get("quantidade") if isinstance(item, dict) else None
        if produto_id is None or not eh_numero(quantidade):
            raise ValidationError("Item inválido: produto_id e quantidade são obrigatórios")
        validados.append({"produto_id": produto_id, "quantidade": quantidade})
    return validados


def criar(dados) -> dict:
    dados = exigir_objeto(dados)
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    usuario_id = como_inteiro(usuario_id)
    if usuario_id is None:
        raise ValidationError("Usuario ID inválido")

    try:
        resultado = pedido_model.criar(usuario_id, _validar_itens(itens))
    except pedido_model.PedidoInvalidoError as err:
        raise ValidationError(str(err), sucesso=False) from None

    notification_service.pedido_criado(resultado["pedido_id"], usuario_id)
    return resultado


def listar(usuario_id: int | None = None) -> list[dict]:
    return pedido_model.listar(usuario_id)


def atualizar_status(pedido_id: int, dados) -> None:
    dados = exigir_objeto(dados, aceita_vazio=True)
    novo_status = dados.get("status", "")
    if novo_status not in STATUS_PEDIDO_VALIDOS:
        raise ValidationError("Status inválido")
    pedido_model.atualizar_status(pedido_id, novo_status)
    notification_service.status_alterado(pedido_id, novo_status)


def relatorio_vendas() -> dict:
    return pedido_model.relatorio_vendas()
