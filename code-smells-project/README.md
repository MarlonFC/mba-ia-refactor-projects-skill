# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
export ADMIN_TOKEN=<token-forte>   # necessário para as rotas administrativas
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas gravadas como hash). Variáveis suportadas: veja `.env.example` (`SECRET_KEY`, `ADMIN_TOKEN`, `FLASK_DEBUG`, `HOST`, `PORT`, `DATABASE_PATH`, `CORS_ORIGINS`, `APP_ENV`).

## Estrutura

```
config/settings.py        # configuração via variáveis de ambiente
models/                   # acesso a dados (SQL parametrizado) + regras de domínio
controllers/              # orquestração dos casos de uso + validação de entrada
views/                    # Blueprints: rotas HTTP e serialização
services/                 # notificações
middlewares/              # error handler central e autenticação admin
app.py                    # create_app() + entry point
```

## Rotas administrativas

Exigem o header `X-Admin-Token` igual a `ADMIN_TOKEN`; sem ele, a resposta é `401`. Sem `ADMIN_TOKEN` configurado, essas rotas ficam sempre fechadas.

- `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`
- `PUT /pedidos/<id>/status`
- `POST /admin/reset-db`

```bash
curl -X DELETE http://localhost:5000/produtos/3 -H "X-Admin-Token: $ADMIN_TOKEN"
```

`POST /admin/query` (execução de SQL arbitrário) foi removido.
