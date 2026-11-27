from models.database import get_db

STATUS_VALIDOS = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]
STATUS_INICIAL = "pendente"
PRODUTO_DESCONHECIDO = "Desconhecido"
# (faturamento acima de, taxa de desconto) — avaliadas em ordem decrescente.
DESCONTO_FAIXAS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))


class PedidoInvalidoError(Exception):
    """Regra de negócio do pedido violada (produto inexistente, estoque insuficiente)."""


def criar(usuario_id: int, itens: list[dict]) -> dict:
    """Cria pedido, itens e baixa estoque numa única transação atômica."""
    db = get_db()
    with db:  # commit no sucesso, rollback em qualquer exceção
        cursor = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, 0)",
            (usuario_id, STATUS_INICIAL),
        )
        pedido_id = cursor.lastrowid
        total = 0
        for item in itens:
            produto_id, quantidade = item["produto_id"], item["quantidade"]
            produto = db.execute("SELECT nome, preco FROM produtos WHERE id = ?", (produto_id,)).fetchone()
            if produto is None:
                raise PedidoInvalidoError(f"Produto {produto_id} não encontrado")
            baixa = db.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (quantidade, produto_id, quantidade),
            )
            if baixa.rowcount == 0:
                raise PedidoInvalidoError(f"Estoque insuficiente para {produto['nome']}")
            db.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (pedido_id, produto_id, quantidade, produto["preco"]),
            )
            total = total + produto["preco"] * quantidade
        db.execute("UPDATE pedidos SET total = ? WHERE id = ?", (total, pedido_id))
    return {"pedido_id": pedido_id, "total": total}


def listar(usuario_id: int | None = None) -> list[dict]:
    """Pedidos com itens em uma única query (sem N+1)."""
    sql = """
        SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
               i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
    """
    params: tuple = ()
    if usuario_id is not None:
        sql += " WHERE p.usuario_id = ?"
        params = (usuario_id,)
    sql += " ORDER BY p.id, i.id"

    pedidos: dict[int, dict] = {}
    for row in get_db().execute(sql, params).fetchall():
        pedido = pedidos.setdefault(row["id"], {
            "id": row["id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        })
        if row["produto_id"] is not None:
            pedido["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or PRODUTO_DESCONHECIDO,
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())


def atualizar_status(pedido_id: int, novo_status: str) -> int:
    db = get_db()
    with db:
        cursor = db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
    return cursor.rowcount


def calcular_desconto(faturamento: float) -> float:
    for limite, taxa in DESCONTO_FAIXAS:
        if faturamento > limite:
            return faturamento * taxa
    return 0


def relatorio_vendas() -> dict:
    row = get_db().execute("""
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               COALESCE(SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END), 0) AS pendentes,
               COALESCE(SUM(CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END), 0) AS aprovados,
               COALESCE(SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END), 0) AS cancelados
        FROM pedidos
    """).fetchone()
    total_pedidos, faturamento = row["total_pedidos"], row["faturamento"]
    desconto = calcular_desconto(faturamento)
    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": row["pendentes"],
        "pedidos_aprovados": row["aprovados"],
        "pedidos_cancelados": row["cancelados"],
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }
