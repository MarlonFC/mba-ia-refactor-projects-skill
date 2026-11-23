# MVC Guidelines — arquitetura-alvo da Fase 3

Em uma API, a "View" é a camada de apresentação HTTP: definição de rotas e serialização da resposta. O alvo é:

```
HTTP request → View/Route → Controller → Model → (banco)
                    ↑            │
                    └── resposta ┘   (erros sobem para o Error Handler central)
```

## 1. Responsabilidades por camada

| Camada | DEVE | NÃO DEVE |
|---|---|---|
| **Config** (`config/`) | Ler configuração de variáveis de ambiente com defaults seguros; expor um objeto/módulo de settings; centralizar constantes de negócio (limites, enums, faixas). | Conter segredos literais; ter lógica de negócio. |
| **Model** (`models/`) | Encapsular acesso a dados (queries parametrizadas/ORM) e **regras de negócio do domínio** (cálculo de total, desconto, estoque, "atrasado", hash de senha); expor funções/métodos com nomes de domínio; executar transações. | Conhecer HTTP (`request`, `res`, status codes, `jsonify`); imprimir/logar respostas. |
| **Controller** (`controllers/`) | Orquestrar o fluxo de um caso de uso: receber dados já extraídos do request, validar regras de entrada, chamar models/serviços, decidir o resultado; lançar erros de domínio (`NotFoundError`, `ValidationError`). | Escrever SQL; acessar a conexão diretamente; montar objetos HTTP de baixo nível quando a view pode fazê-lo; conter regras de cálculo de negócio. |
| **View / Routes** (`views/` ou `routes/`) | Declarar rotas (método + path), extrair parâmetros/body, chamar **um** controller, serializar a resposta (status + JSON). | Regra de negócio, queries, `try/except` por rota. |
| **Middlewares** (`middlewares/`) | Error handler central (mapeia exceções → status/JSON), autenticação de rotas admin, logging de requisição. | Regras de domínio. |
| **Services** (`services/`, opcional) | Integrações externas (e-mail, pagamento, filas) atrás de interface simples, injetadas no controller. | Ser depósito de regras de domínio que pertencem ao model. |
| **Composition root** (`app.py` / `src/app.js`) | Criar a app, carregar config, inicializar banco, registrar middlewares, views e error handler; iniciar o servidor. | Definir rotas de negócio ou SQL. |

**Regra de dependência:** `views → controllers → models` (e `controllers → services`). Nunca o contrário. `config` pode ser importado por todos. Models não importam controllers/views.

## 2. Estrutura-alvo por stack

Adapte nomes ao domínio (um arquivo por entidade/agregado por camada). O **comando de start original continua funcionando** (mesmo arquivo de entrada ou um shim que delega).

### Python / Flask (sem `src/`, pacotes na raiz — mantém `python app.py`)
```
config/settings.py            # Settings a partir de os.environ (+ constantes de negócio)
models/database.py            # conexão/sessão + init/seed (sem estado global mutável)
models/<entidade>_model.py    # dados + regras do domínio
controllers/<entidade>_controller.py
views/<entidade>_routes.py    # Blueprints; serialização
middlewares/error_handler.py  # AppError + register_error_handlers(app)
middlewares/auth.py           # require_admin (se houver rotas admin)
app.py                        # create_app() + if __name__ == "__main__"
```
Com Flask-SQLAlchemy: `database.py` (ou `models/__init__.py`) mantém o `db = SQLAlchemy()`; classes ORM ficam em `models/`.

### Node.js / Express (dentro de `src/` — mantém `npm start`)
```
src/config/index.js           # process.env + constantes
src/models/database.js        # conexão + schema/seed; helpers promisificados
src/models/<entidade>Model.js
src/controllers/<entidade>Controller.js
src/views/<entidade>Routes.js # express.Router()
src/middlewares/errorHandler.js
src/middlewares/auth.js
src/app.js                    # composition root + listen
```

### Outras stacks
Mesma separação com convenções locais: FastAPI (`routers/` = views, `schemas/` = serialização), Spring (`@RestController` = view, `@Service` = controller/caso de uso, `@Repository`/entidades = model), Go (`handlers/` = view, `usecase/` = controller, `repository/` + `domain/` = model).

## 3. Estratégia de adaptação

Decida com base na classificação da Fase 1:

**Monolítico** (ex.: tudo em 3–5 arquivos, God Class/Module)
1. Criar a estrutura completa da §2.
2. Fatiar o god module por **domínio** e por **camada** ao mesmo tempo.
3. Remover os arquivos originais quando esvaziarem (não deixar `models.py` legado convivendo com `models/`).

**Parcialmente em camadas** (ex.: `models/`, `routes/`, `services/`, `utils/` já existem)
1. **Preservar** o que está adequado (ex.: classes ORM em `models/`, blueprints) — não renomear por estética.
2. **Adicionar** o que falta: `config/`, `controllers/`, `middlewares/error_handler`.
3. **Mover** responsabilidades fora do lugar: regras de `routes/` → `models/` (regras do domínio) e `controllers/` (fluxo); rotas de uma entidade em arquivo de outra → arquivo próprio.
4. **Reaproveitar** helpers/métodos existentes que estavam ignorados (ex.: `Task.is_overdue()`, constantes em `utils/`) em vez de criar novos; apagar os que continuarem sem uso.
5. A pasta `routes/` pode continuar com esse nome (é a camada View); documente o mapeamento `routes/ = Views`.

**Já em camadas:** apenas corrigir os findings, sem reestruturar.

## 4. Ordem de refatoração

1. **Config** — extrair settings/segredos/constantes (PB-01, PB-15).
2. **Dados/Models** — conexão sem estado global, queries parametrizadas, transações, N+1, regras de domínio (PB-02, PB-03, PB-07, PB-08, PB-09, PB-06).
3. **Controllers** — fluxo + validação (PB-06, PB-11).
4. **Views/Routes** — rotas finas, mesmos paths e métodos (PB-05).
5. **Middlewares** — error handler central, auth admin (PB-12, PB-04).
6. **Composition root / entry point** — `create_app()`/`app.js` (PB-05, PB-07).
7. **Limpeza** — deprecated APIs, código morto, nomes, logging (PB-13, PB-15).

Verifique compilação/import após cada etapa.

## 5. Mudanças de contrato permitidas

O contrato (rotas, métodos, status de sucesso, campos de entrada, formato JSON) é preservado, **exceto**:

| Mudança | Condição |
|---|---|
| Remover campos sensíveis das respostas (`senha`, `password`, hash, `secret_key`, número de cartão) | Sempre. |
| Rotas `/admin/*`, execução de SQL arbitrário, reset de banco e relatórios administrativos passam a exigir token admin (`X-Admin-Token` comparado a `ADMIN_TOKEN` da config) → `401` sem token | Sempre que AP-04 for CRITICAL. Validação usa o header. Se `ADMIN_TOKEN` não estiver configurado, a rota responde `401/403` (seguro por padrão). |
| Entrada inválida que antes gerava `500` passa a gerar `400`/`404` | Quando a correção de validação/erro (PB-11/PB-12) mudar o status de um caso de erro. |
| Ataque deixa de funcionar (ex.: SQL Injection no login → `401`) | Sempre. |
| Mensagem de erro interna (`str(e)`) substituída por mensagem genérica | Sempre; detalhe vai para o log. |
| Timestamps continuam com o mesmo formato textual | Ao modernizar datetime, manter naive UTC (ver PB-13) para não mudar `str()` da resposta. |

Toda mudança aplicada deve aparecer em "Intentional Contract Changes" no resumo da Fase 3. **Não** invente autenticação para rotas comuns (isso quebraria clientes): reporte o risco e recomende.

## 6. Convenções

- Nomes no idioma do domínio original (ex.: `produto_model.py` se o código é em português).
- Um export público por responsabilidade; funções pequenas.
- Erros de domínio como exceções/classes (`AppError(status, message)`) tratadas no handler central.
- Logger da stack (`logging.getLogger(__name__)`, `console` encapsulado em `logger.js` só se necessário) em vez de `print`.
- Sem dependências novas quando stdlib/framework resolve (Werkzeug para hash de senha em Flask; `crypto.scrypt` no Node).
