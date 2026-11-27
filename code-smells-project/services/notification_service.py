import logging

logger = logging.getLogger(__name__)


def pedido_criado(pedido_id: int, usuario_id: int) -> None:
    # Integrações reais (e-mail/SMS/push) entram aqui; hoje apenas registra o evento.
    logger.info("ENVIANDO EMAIL: Pedido %s criado para usuario %s", pedido_id, usuario_id)
    logger.info("ENVIANDO SMS: Seu pedido foi recebido!")
    logger.info("ENVIANDO PUSH: Novo pedido recebido pelo sistema")


def status_alterado(pedido_id: int, novo_status: str) -> None:
    if novo_status == "aprovado":
        logger.info("NOTIFICAÇÃO: Pedido %s foi aprovado! Preparar envio.", pedido_id)
    elif novo_status == "cancelado":
        logger.info("NOTIFICAÇÃO: Pedido %s cancelado. Devolver estoque.", pedido_id)
