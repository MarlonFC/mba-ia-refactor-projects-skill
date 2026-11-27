# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
ADMIN_TOKEN=<token> npm start
```

A aplicação sobe em `http://localhost:3000` (`PORT` altera a porta). O banco SQLite é em memória (`DB_PATH`) e já carrega seeds automaticamente no boot.
Variáveis de ambiente: veja `.env.example`.

As rotas administrativas (`GET /api/admin/financial-report`, `DELETE /api/users/:id`) exigem o header `X-Admin-Token` igual a `ADMIN_TOKEN`; sem ele (ou sem `ADMIN_TOKEN` configurado) respondem `401`.

## Estrutura

```
src/
  app.js            # composition root (injeção de dependências + listen)
  config/           # configuração via process.env
  models/           # conexão/schema/seed e acesso a dados por entidade
  services/         # casos de uso (checkout, relatório, exclusão de usuário)
  controllers/      # entrada/saída HTTP
  routes/           # mapeamento de rotas (camada View)
  middlewares/      # auth admin e error handler central
```

Exemplos de requisições estão em `api.http`.
