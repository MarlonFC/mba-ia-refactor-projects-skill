import logging

from controllers.validation import optional_float, require_json, require_number, require_str
from middlewares.error_handler import NotFoundError, ValidationError
from models import produto_model

logger = logging.getLogger(__name__)


def _extrair_produto(dados) -> dict:
    """Validação comum a criar e atualizar (mesmas mensagens do contrato original)."""
    dados = require_json(dados)
    for campo, mensagem in (("nome", "Nome é obrigatório"),
                            ("preco", "Preço é obrigatório"),
                            ("estoque", "Estoque é obrigatório")):
        if campo not in dados:
            raise ValidationError(mensagem)

    produto = {
        "nome": require_str(dados["nome"], "Nome deve ser texto"),
        "descricao": require_str(dados.get("descricao", ""), "Descrição deve ser texto"),
        "preco": require_number(dados["preco"], "Preço deve ser numérico"),
        "estoque": require_number(dados["estoque"], "Estoque deve ser numérico"),
        "categoria": require_str(dados.get("categoria", produto_model.CATEGORIA_PADRAO), "Categoria inválida"),
    }
    if produto["preco"] < 0:
        raise ValidationError("Preço não pode ser negativo")
    if produto["estoque"] < 0:
        raise ValidationError("Estoque não pode ser negativo")
    return produto


def listar() -> list[dict]:
    produtos = produto_model.listar()
    logger.info("Listando %s produtos", len(produtos))
    return produtos


def buscar(produto_id: int) -> dict:
    produto = produto_model.buscar_por_id(produto_id)
    if not produto:
        raise NotFoundError("Produto não encontrado", sucesso=False)
    return produto


def criar(dados) -> int:
    produto = _extrair_produto(dados)
    nome = produto["nome"]
    if len(nome) < produto_model.NOME_MIN_LENGTH:
        raise ValidationError("Nome muito curto")
    if len(nome) > produto_model.NOME_MAX_LENGTH:
        raise ValidationError("Nome muito longo")
    if produto["categoria"] not in produto_model.CATEGORIAS_VALIDAS:
        raise ValidationError(f"Categoria inválida. Válidas: {produto_model.CATEGORIAS_VALIDAS}")

    produto_id = produto_model.criar(**produto)
    logger.info("Produto criado com ID: %s", produto_id)
    return produto_id


def atualizar(produto_id: int, dados) -> None:
    if not produto_model.buscar_por_id(produto_id):
        raise NotFoundError("Produto não encontrado")
    # O update original não aplica limites de nome nem lista de categorias; mantido para preservar o contrato.
    produto_model.atualizar(produto_id, **_extrair_produto(dados))


def deletar(produto_id: int) -> None:
    if not produto_model.buscar_por_id(produto_id):
        raise NotFoundError("Produto não encontrado")
    produto_model.deletar(produto_id)
    logger.info("Produto %s deletado", produto_id)


def pesquisar(termo: str, categoria: str | None, preco_min: str | None, preco_max: str | None) -> list[dict]:
    return produto_model.buscar(
        termo,
        categoria,
        optional_float(preco_min, "preco_min"),
        optional_float(preco_max, "preco_max"),
    )
