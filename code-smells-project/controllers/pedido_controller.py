from controllers.validation import require_id, require_int, require_json
from middlewares.error_handler import ValidationError
from models import pedido_model
from services import notification_service


def _validar_itens(itens) -> list[dict]:
    if not isinstance(itens, list):
        raise ValidationError("Itens devem ser uma lista")
    validados = []
    for item in itens:
        if not isinstance(item, dict):
            raise ValidationError("Item inválido")
        validados.append({
            "produto_id": require_id(item.get("produto_id"), "produto_id deve ser inteiro"),
            "quantidade": require_int(item.get("quantidade"), "quantidade deve ser inteira"),
        })
    return validados


def criar(dados) -> dict:
    dados = require_json(dados)
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    usuario_id = require_id(usuario_id, "Usuario ID deve ser inteiro")

    try:
        resultado = pedido_model.criar(usuario_id, _validar_itens(itens))
    except pedido_model.PedidoInvalidoError as err:
        raise ValidationError(str(err), sucesso=False) from None

    notification_service.pedido_criado(resultado["pedido_id"], usuario_id)
    return resultado


def listar_todos() -> list[dict]:
    return pedido_model.listar()


def listar_do_usuario(usuario_id: int) -> list[dict]:
    return pedido_model.listar(usuario_id)


def atualizar_status(pedido_id: int, dados) -> None:
    dados = dados if isinstance(dados, dict) else {}
    novo_status = dados.get("status", "")
    if novo_status not in pedido_model.STATUS_VALIDOS:
        raise ValidationError("Status inválido")

    pedido_model.atualizar_status(pedido_id, novo_status)
    notification_service.status_alterado(pedido_id, novo_status)


def relatorio_vendas() -> dict:
    return pedido_model.relatorio_vendas()
