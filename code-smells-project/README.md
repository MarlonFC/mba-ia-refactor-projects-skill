# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo.

## Configuração

Variáveis de ambiente (ver `.env.example`):

| Variável | Padrão | Uso |
|---|---|---|
| `SECRET_KEY` | gerada a cada boot | chave da aplicação Flask |
| `ADMIN_TOKEN` | — (rotas admin fechadas) | exigido no header `X-Admin-Token` em `/admin/*` |
| `APP_DEBUG` | `false` | modo debug |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | bind do servidor (use `HOST=0.0.0.0` em container) |
| `DATABASE_PATH` | `loja.db` | arquivo SQLite |
| `CORS_ORIGINS` | `*` | origens permitidas, separadas por vírgula |
| `APP_ENV` | `producao` | valor exibido em `/health` |

## Estrutura

```
app.py            composition root (create_app)
config/           settings e constantes de negócio
models/           conexão, SQL e regras de domínio
controllers/      casos de uso e validação de entrada
views/            rotas (Blueprints) e serialização JSON
middlewares/      error handler central e auth admin
services/         notificações
```
