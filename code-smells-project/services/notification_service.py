"""Notificações de pedido. Hoje apenas registra em log (mesmo efeito observável do código original)."""
import logging

from config.settings import STATUS_APROVADO, STATUS_CANCELADO

logger = logging.getLogger(__name__)


def pedido_criado(pedido_id: int, usuario_id: int) -> None:
    logger.info("Notificação (email/sms/push): pedido %s criado para usuário %s", pedido_id, usuario_id)


def status_alterado(pedido_id: int, novo_status: str) -> None:
    if novo_status == STATUS_APROVADO:
        logger.info("Notificação: pedido %s aprovado, preparar envio", pedido_id)
    elif novo_status == STATUS_CANCELADO:
        logger.info("Notificação: pedido %s cancelado", pedido_id)
