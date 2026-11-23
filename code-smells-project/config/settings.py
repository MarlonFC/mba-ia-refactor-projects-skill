"""Configuração de runtime (variáveis de ambiente) e constantes de negócio."""
import os
import secrets


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # Sem segredo literal: usa env ou gera um efêmero (sessões invalidam a cada restart).
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _env_bool("APP_DEBUG", False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")  # sem default: rotas admin fechadas
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    ENVIRONMENT = os.getenv("APP_ENV", "producao")


API_VERSION = "1.0.0"

# Produtos
CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"
NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

# Pedidos
STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_PEDIDO_VALIDOS = [STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO]

# Relatório de vendas: (faturamento acima de, taxa de desconto), da maior faixa para a menor.
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))

# Usuários
TIPO_USUARIO_PADRAO = "cliente"
