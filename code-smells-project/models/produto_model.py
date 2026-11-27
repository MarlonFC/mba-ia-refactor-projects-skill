from models.database import get_db

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"
NOME_MIN_LENGTH = 2
NOME_MAX_LENGTH = 200


def _produto_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def listar() -> list[dict]:
    rows = get_db().execute("SELECT * FROM produtos").fetchall()
    return [_produto_to_dict(row) for row in rows]


def buscar_por_id(produto_id: int) -> dict | None:
    row = get_db().execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return _produto_to_dict(row) if row else None


def criar(nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> int:
    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(produto_id: int, nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> int:
    db = get_db()
    with db:
        cursor = db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )
    return cursor.rowcount


def deletar(produto_id: int) -> int:
    # itens_pedido não é apagado: o histórico financeiro dos pedidos é preservado (PB-16).
    db = get_db()
    with db:
        cursor = db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    return cursor.rowcount


def buscar(termo: str, categoria: str | None = None,
           preco_min: float | None = None, preco_max: float | None = None) -> list[dict]:
    conditions, params = ["1=1"], []
    if termo:
        conditions.append("(nome LIKE ? OR descricao LIKE ?)")
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        conditions.append("categoria = ?")
        params.append(categoria)
    if preco_min:
        conditions.append("preco >= ?")
        params.append(preco_min)
    if preco_max:
        conditions.append("preco <= ?")
        params.append(preco_max)
    # Só fragmentos fixos são interpolados; valores vão como parâmetros.
    rows = get_db().execute(f"SELECT * FROM produtos WHERE {' AND '.join(conditions)}", params).fetchall()
    return [_produto_to_dict(row) for row in rows]
