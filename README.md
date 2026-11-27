# refactor-arch — Refatoração Arquitetural Automatizada com Skills

Skill para **Claude Code** que analisa, audita e refatora projetos backend para o padrão **MVC**, independente da stack. Foi aplicada aos três projetos legados deste repositório (fork de [devfullcycle/mba-ia-refactor-projects-skill](https://github.com/devfullcycle/mba-ia-refactor-projects-skill), onde está o enunciado original):

| Projeto | Stack | Domínio |
|---|---|---|
| `code-smells-project/` | Python 3 + Flask 3.1 + sqlite3 | E-commerce (produtos, usuários, pedidos) |
| `ecommerce-api-legacy/` | Node.js 22 + Express 4 + sqlite3 (memória) | LMS com checkout (cursos, matrículas, pagamentos) |
| `task-manager-api/` | Python 3 + Flask 3.0 + Flask-SQLAlchemy | Task Manager (tasks, usuários, categorias) |

```
.
├── README.md
├── reports/audit-project-{1,2,3}.md        # saída da Fase 2 de cada projeto
├── code-smells-project/
│   ├── .claude/skills/refactor-arch/       # skill (cópia idêntica nos 3 projetos)
│   └── .refactor-arch/                     # evidências da execução (relatório, requests, antes/depois, logs)
├── ecommerce-api-legacy/  (mesma organização)
└── task-manager-api/      (mesma organização)
```

**Resultado:** os 4 critérios de aceite foram atingidos nos 3 projetos (stack detectada, ≥ 5 findings, ≥ 1 CRITICAL/HIGH, aplicação funcionando após a refatoração).

---

## A) Análise Manual

Feita **antes** de escrever a skill, lendo o código e executando as aplicações originais. As linhas referem-se ao commit original `6d1ce62`. Itens marcados com ✅ foram confirmados em execução (ex.: o SQL Injection no login foi explorado de fato).

Escala: **CRITICAL** (segurança / separação de responsabilidades totalmente violada) · **HIGH** (violação forte de MVC/SOLID) · **MEDIUM** (duplicação, N+1, validação ausente) · **LOW** (legibilidade, nomes, magic numbers).

### Projeto 1 — code-smells-project (Python 3 / Flask 3.1.1 / sqlite3 puro)

Domínio: API de e-commerce (produtos, usuários, pedidos, relatório de vendas). 4 arquivos, ~780 linhas, 18 endpoints. Arquitetura monolítica: `app.py` (rotas + endpoints admin), `controllers.py` (HTTP + validação + regras), `models.py` (SQL + regras + serialização), `database.py` (conexão global + schema + seed).

| # | Sev. | Problema | Local | Justificativa |
|---|---|---|---|---|
| 1 | CRITICAL | **SQL Injection** em praticamente todas as queries (concatenação de strings) | `models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 157-166, 174, 188, 192, 279-281, 289-297` | ✅ `POST /login` com `email = "admin@loja.com' --"` autentica como **admin sem senha**. Permite ler/alterar/apagar qualquer dado. |
| 2 | CRITICAL | **Endpoints administrativos sem autenticação**, incluindo execução de SQL arbitrário | `app.py:47-57` (`/admin/reset-db`), `app.py:59-78` (`/admin/query`) | Qualquer cliente apaga o banco ou executa `DROP TABLE`. É um RCE de banco "by design". |
| 3 | CRITICAL | **Credenciais hardcoded e vazadas na API** | `app.py:7` (`SECRET_KEY`), `controllers.py:285-289` (`/health` devolve `secret_key`, `db_path`, `debug`) | ✅ `GET /health` expõe a chave. Segredo versionado no git = comprometido. |
| 4 | CRITICAL | **Senhas em texto plano**, armazenadas e devolvidas pela API | `database.py:75-79` (seed), `models.py:126-129` (insert), `models.py:110` (comparação), `models.py:83, 99` (`senha` no retorno) | ✅ `GET /usuarios/1` retorna `"senha": "admin123"`. Vazamento de credenciais de todos os usuários. |
| 5 | CRITICAL | **God Module**: `models.py` concentra SQL, regras de negócio (estoque, desconto), serialização e 4 domínios; rotas também executam SQL direto | `models.py:1-314`, `app.py:47-78`, `controllers.py:264-292` | Nenhuma camada é testável isoladamente; qualquer mudança afeta tudo. |
| 6 | HIGH | **Estado global mutável**: conexão única compartilhada entre threads (`check_same_thread=False`), sem rollback | `database.py:4-5, 7-10` | Requisições concorrentes compartilham a mesma transação; uma escrita pela metade pode ser "commitada" por outra requisição. |
| 7 | HIGH | **Criação de pedido não atômica** (check-then-act no estoque, sem transação/rollback) | `models.py:133-169` | Corrida pode vender estoque inexistente; falha no meio deixa pedido sem itens. |
| 8 | HIGH | **Regras de negócio e efeitos colaterais no controller** (lista de categorias, limites, "envio" de e-mail/SMS/push) | `controllers.py:43-54, 208-210, 247-250` | Viola MVC/SRP; regra de cancelamento promete "devolver estoque" (`:250`) mas não faz. |
| 9 | HIGH | **Debug ligado e bind em 0.0.0.0** | `app.py:8, 88` | Debugger do Werkzeug exposto na rede permite execução de código. |
| 10 | MEDIUM | **N+1 queries** ao listar pedidos (1 query por pedido + 1 por item) | `models.py:171-201, 203-233` | Custo cresce linearmente com pedidos × itens. |
| 11 | MEDIUM | **Código duplicado**: mapeamento row→dict repetido; duas funções de pedidos quase idênticas; validação de produto duplicada | `models.py:12-21, 31-40, 304-313`; `models.py:171-201` vs `203-233`; `controllers.py:28-50` vs `72-90` | Correções precisam ser replicadas em N lugares (e já divergiram: update não valida categoria/nome). |
| 12 | MEDIUM | **Validação ausente/inconsistente** | `controllers.py:169-170, 239-240` (body nulo → `AttributeError` 500), `:43-46` (tipo de `preco` não checado → 500), `:146-165` (sem formato/duplicidade de e-mail) | Entradas inválidas viram erro 500 em vez de 400. |
| 13 | MEDIUM | **Error handling espalhado e vazando internals** (`try/except Exception` + `str(e)` em cada handler) | `controllers.py:10-12, 21-22, 60-62, …, 291-292`; `app.py:77-78` | Sem handler central; mensagens internas expostas ao cliente. |
| 14 | MEDIUM | **CORS aberto para qualquer origem** | `app.py:9` | Qualquer site pode chamar a API a partir do navegador. |
| 15 | LOW | **Magic numbers** (faixas e percentuais de desconto, limites de nome, porta) | `models.py:257-262`, `controllers.py:47-50`, `app.py:88` | Regra de negócio sem nome; difícil de ajustar. |
| 16 | LOW | **`print` como logging** (inclui e-mail do usuário = PII) | `controllers.py:8, 57, 106, 161, 179, 182, 208-210, 219, 248, 250`; `app.py:56, 83-86` | Sem nível, sem destino configurável. |
| 17 | LOW | **Nomes ruins**: `id` sombreando builtin, `cursor2`/`cursor3` | `controllers.py:14, 56, 160`; `models.py:24, 187, 191` | Legibilidade. |
| 18 | LOW | **Imports não usados** | `models.py:2` (`sqlite3`), `database.py:2` (`os`) | Ruído. |

**APIs deprecated:** nenhuma no código (Flask 3.1 atual). Não se aplica.

---

### Projeto 2 — ecommerce-api-legacy (Node.js 22 / Express ^4.18 / sqlite3 ^5, banco em memória)

Domínio: LMS com checkout (cursos, matrículas, pagamentos, relatório financeiro). 3 arquivos, ~180 linhas, 3 endpoints. Arquitetura: `AppManager` é uma classe única com conexão, schema, seed, rotas e regras; `utils.js` mistura config, cache global e "hash".

| # | Sev. | Problema | Local | Justificativa |
|---|---|---|---|---|
| 1 | CRITICAL | **Credenciais hardcoded** (senha de banco, chave *live* do gateway de pagamento, usuário SMTP) | `src/utils.js:1-7` | Segredos de produção versionados. |
| 2 | CRITICAL | **Dados de cartão e chave do gateway em log** | `src/AppManager.js:45` | Número completo do cartão em log viola PCI-DSS. |
| 3 | CRITICAL | **Hash de senha inseguro** (`badCrypto` = prefixo base64 repetido, truncado em 10 chars), seed em texto plano e senha padrão `123456` | `src/utils.js:17-23`; `src/AppManager.js:18, 68` | Hash trivialmente reversível/colidível; contas criadas sem senha recebem senha conhecida. |
| 4 | CRITICAL | **God Class `AppManager`**: conexão, DDL, seed, roteamento, pagamento, matrícula e relatório na mesma classe | `src/AppManager.js:4-139` | Zero separação de camadas; impossível testar regras sem subir HTTP + banco. |
| 5 | HIGH | **Sem autenticação/autorização**: relatório financeiro e delete de usuário públicos; checkout com e-mail existente matricula sem checar senha | `src/AppManager.js:80, 131, 40-75` | ✅ checkout com e-mail de `leonan@…` e sem `pwd` retornou 200. Expõe faturamento e nomes de alunos. |
| 6 | HIGH | **Lógica de negócio no handler + callback hell** (5 níveis; aprovação de pagamento = "cartão começa com 4") | `src/AppManager.js:28-78` | Regra de pagamento inacessível para teste/reuso; fluxo difícil de seguir. |
| 7 | HIGH | **Checkout não transacional** (matrícula, pagamento e auditoria em inserts independentes) | `src/AppManager.js:50-61` | Falha no pagamento deixa matrícula sem pagamento. |
| 8 | HIGH | **Estado global mutável** (`globalCache` sem limite, `totalRevenue` exportado por valor e nunca usado) | `src/utils.js:9-10, 12-15, 25` | Vazamento de memória e estado compartilhado invisível. |
| 9 | MEDIUM | **N+1 queries** no relatório financeiro (1 query por curso, 2 por matrícula) | `src/AppManager.js:83-128` | Escala com cursos × matrículas; um único `JOIN` resolve. |
| 10 | MEDIUM | **Erros ignorados / respostas inconsistentes**: `err` descartado; respostas em texto puro misturadas com JSON; sem middleware de erro | `src/AppManager.js:57, 92-93, 104, 106, 133-135`; `:35, 38, 41` | Se a query de `:92` falhar, `enrollments.length` derruba o processo. |
| 11 | MEDIUM | **Delete sem integridade referencial** e sempre 200 (mesmo para id inexistente) | `src/AppManager.js:131-137` | ✅ após `DELETE /api/users/1`, relatório mostra aluno "Unknown" (dados órfãos). |
| 12 | MEDIUM | **Validação de entrada mínima** (só presença; sem formato de e-mail, tipo de `c_id`, formato de cartão) | `src/AppManager.js:35` | Dados inválidos chegam ao banco. |
| 13 | LOW | **Nomes crípticos** (`u`, `e`, `p`, `cid`, `cc`) | `src/AppManager.js:29-33` | Legibilidade (o contrato `usr/eml/pwd/c_id` da API deve ser mantido). |
| 14 | LOW | **Magic values** (`"4"`, `'PAID'`/`'DENIED'`, `10000`, porta `3000`) | `src/AppManager.js:46`; `src/utils.js:6, 19` | Regras sem nome. |
| 15 | LOW | **Imports/exports mortos e estilo inconsistente** (`totalRevenue` importado e não usado; `let` para constantes; `self = this` misturado com arrow functions) | `src/AppManager.js:2, 26, 29-33` | Ruído e confusão de escopo. |
| 16 | LOW | **`console.log` como logging** | `src/app.js:13`; `src/utils.js:13` | Sem níveis/destino. |

**APIs deprecated:** nenhuma no código-fonte. Só um aviso transitivo do `npm install` (`tar@6`, puxado pelo `sqlite3`), que deve ser apenas reportado.

---

### Projeto 3 — task-manager-api (Python 3 / Flask 3.0 / Flask-SQLAlchemy 3.1 + SQLAlchemy 2.1)

Domínio: Task Manager (tasks, usuários, categorias, relatórios). 15 arquivos `.py`, ~1.160 linhas, 22 endpoints. Arquitetura parcial: `models/` (ORM), `routes/` (Blueprints que fazem **tudo**), `services/` (notificação não usada), `utils/` (helpers majoritariamente não usados). Não há camada de controller/serviço de domínio nem config.

| # | Sev. | Problema | Local | Justificativa |
|---|---|---|---|---|
| 1 | CRITICAL | **Credenciais hardcoded** (`SECRET_KEY`, senha SMTP) | `app.py:13`; `services/notification_service.py:7-10` | Segredos versionados. |
| 2 | CRITICAL | **Hash de senha MD5 sem salt** | `models/user.py:27-32` | MD5 é quebrável por rainbow table em segundos. |
| 3 | CRITICAL | **Hash da senha exposto nas respostas** (`to_dict` inclui `password`) | `models/user.py:16-25`, usado em `routes/user_routes.py:33, 85, 129, 209` | ✅ `GET /users/1` retorna `81dc9bdb…` = `md5("1234")`. |
| 4 | HIGH | **Autenticação falsa e escalonamento de privilégio**: token previsível `fake-jwt-token-<id>`, nenhuma rota protegida, `role` (inclusive `admin`) aceito do corpo da requisição | `routes/user_routes.py:210, 52, 71-72, 119-122` | Qualquer cliente cria um admin ou forja um token. |
| 5 | HIGH | **Rotas "gordas"**: validação, regra de negócio, serialização e acesso a dados no handler; não existe camada de controller | `routes/task_routes.py:11-299`, `routes/user_routes.py:42-151`, `routes/report_routes.py:12-155` | Camadas existem só no nome; regras não são reutilizáveis nem testáveis. |
| 6 | HIGH | **Debug ligado e bind em 0.0.0.0** | `app.py:34` | Debugger do Werkzeug exposto. |
| 7 | MEDIUM | **API deprecated: `datetime.utcnow()`** (deprecated no Python 3.12+) → `datetime.now(timezone.utc)` | `models/task.py:15-16, 52`; `models/user.py:14`; `models/category.py:11`; `routes/task_routes.py:31, 72, 215, 285`; `routes/user_routes.py:172`; `routes/report_routes.py:35, 42, 45, 71, 133`; `utils/helpers.py:38`; `services/notification_service.py:35`; `seed.py:66-69, 74` | ✅ `DeprecationWarning` emitido ao rodar `seed.py` no Python 3.13. |
| 8 | MEDIUM | **API legacy: `Model.query.get(id)`** (legacy no SQLAlchemy 2.x) → `db.session.get(Model, id)` | `routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227`; `routes/user_routes.py:29, 94, 136, 155`; `routes/report_routes.py:105, 192, 213` | ✅ `LegacyAPIWarning` emitido com SQLAlchemy 2.1.9. |
| 9 | MEDIUM | **N+1 queries** | `routes/task_routes.py:41-57`; `routes/user_routes.py:22`; `routes/report_routes.py:55-56, 162-163` | 1 query extra por task/usuário/categoria. |
| 10 | MEDIUM | **Lógica duplicada ignorando o que já existe**: cálculo de "overdue" copiado 6× enquanto `Task.is_overdue()` não é usado; `process_task_data` e constantes `VALID_*` não usados enquanto as rotas repetem listas literais; serialização de task reescrita à mão | `routes/task_routes.py:30-39, 71-80, 283-287`; `routes/user_routes.py:171-180`; `routes/report_routes.py:34-43, 132-135`; `models/task.py:50-60`; `utils/helpers.py:57-116`; `routes/task_routes.py:17-28` | As cópias divergem (create aceita só `%Y-%m-%d`, o helper aceita 2 formatos). |
| 11 | MEDIUM | **`except:` genérico / sem handler central** | `routes/task_routes.py:62, 137, 204, 236`; `routes/user_routes.py:130, 149`; `routes/report_routes.py:186, 207, 221`; `utils/helpers.py:46, 49, 88` | Captura até `KeyboardInterrupt`; esconde a causa real. |
| 12 | MEDIUM | **Validação ausente** (tipo de `priority` → `TypeError` 500; body nulo em `PUT /categories` → 500; cor não validada apesar de `is_valid_color` existir) | `routes/task_routes.py:113, 182`; `routes/report_routes.py:196-202, 180`; `utils/helpers.py:52-55` | Erros de cliente viram 500. |
| 13 | MEDIUM | **Múltiplas queries de contagem** em vez de `GROUP BY` (12 `COUNT` por relatório) | `routes/report_routes.py:15-28`; `routes/task_routes.py:275-279` | Ida e volta desnecessária ao banco. |
| 14 | MEDIUM | **Responsabilidade mal posicionada**: CRUD de categorias dentro de `report_routes.py`; delete de categoria deixa tasks com FK órfã | `routes/report_routes.py:157-223, 217-219` | Organização enganosa; integridade referencial. |
| 15 | LOW | **Imports não usados** | `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`; `routes/report_routes.py:8`; `utils/helpers.py:3-7`; `models/task.py:3` | Ruído. |
| 16 | LOW | **Magic numbers/strings** (prioridade 1–5, título 3/200, senha ≥4, `'#000000'`, mapeamento p1..p5) | `routes/task_routes.py:96-114`; `routes/user_routes.py:64`; `routes/report_routes.py:24-28, 84-88, 180` | Constantes já existem em `helpers.py:110-116` mas não são usadas. |
| 17 | LOW | **Booleanos verbosos / `if` aninhados** (`if x: return True else: return False`) | `models/user.py:34-38`; `models/task.py:38-60`; `utils/helpers.py:21-23, 53-55` | Legibilidade. |
| 18 | LOW | **`type(x) == list`** em vez de `isinstance`; **`print` como logging** | `routes/task_routes.py:141, 210`; `utils/helpers.py:103`; `routes/task_routes.py:149, 153, 219, 234`; `routes/user_routes.py:83, 89, 147` | Idiomático/observabilidade. |

---

### Resumo

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| 1 — code-smells-project | 5 | 4 | 5 | 4 | 18 |
| 2 — ecommerce-api-legacy | 4 | 4 | 4 | 4 | 16 |
| 3 — task-manager-api | 3 | 3 | 8 | 4 | 18 |

Todos atendem ao mínimo (≥1 CRITICAL/HIGH, ≥2 MEDIUM, ≥2 LOW).

### Padrões transversais → insumo para o catálogo da skill

| Anti-pattern genérico | P1 | P2 | P3 | Sinal de detecção (agnóstico) |
|---|---|---|---|---|
| Hardcoded secrets | ✔ | ✔ | ✔ | literal atribuído a `*key*`, `*secret*`, `*pass*`, `*token*`, `SECRET_KEY`, `pk_live_` |
| SQL Injection | ✔ | – | – | SQL montado com `+`, f-string, template string ou `%` contendo variável |
| Senha fraca/plana/exposta | ✔ | ✔ | ✔ | `md5`/`sha1`/base64 em senha; coluna senha no serializer de resposta |
| Endpoint sensível sem auth | ✔ | ✔ | ✔ | rotas `admin`/`delete`/`query` sem decorator/middleware de auth |
| God Class / God Module | ✔ | ✔ | – | arquivo/classe com SQL + regra + HTTP; >300 linhas cobrindo >1 domínio |
| Lógica de negócio em rota/controller | ✔ | ✔ | ✔ | cálculos, regras e chamadas ao banco dentro do handler |
| Estado global mutável | ✔ | ✔ | – | `global`, `let` de módulo mutado, conexão singleton compartilhada |
| Transação ausente em fluxo multi-escrita | ✔ | ✔ | – | ≥2 escritas relacionadas sem `BEGIN/COMMIT/ROLLBACK` |
| Debug/bind inseguros | ✔ | – | ✔ | `debug=True`, `host='0.0.0.0'` fixos |
| N+1 | ✔ | ✔ | ✔ | query dentro de `for`/`forEach` |
| Duplicação | ✔ | – | ✔ | blocos ≥5 linhas iguais; helper existente não usado |
| Error handling ad-hoc | ✔ | ✔ | ✔ | `try/except` por handler, `except:` genérico, `err` ignorado, `str(e)` no response |
| Validação ausente | ✔ | ✔ | ✔ | campos de `request` usados sem checar tipo/nulo |
| APIs deprecated | – | (dep. transitiva) | ✔ | `datetime.utcnow`, `Query.get`, `new Buffer`, `body-parser`, `url.parse`… |
| Magic numbers / nomes ruins / logging com print / imports mortos | ✔ | ✔ | ✔ | literais numéricos em condição; identificadores de 1–2 letras; `print`/`console.log` |

---

## B) Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                          # orquestração das 3 fases (o "prompt")
├── references/
│   ├── project-analysis.md           # Análise de projeto
│   ├── anti-patterns-catalog.md      # Catálogo de anti-patterns (+ APIs deprecated)
│   ├── audit-report-template.md      # Template de relatório
│   ├── mvc-guidelines.md             # Guidelines de arquitetura
│   ├── refactoring-playbook.md       # Playbook de refatoração
│   └── validation-guide.md           # Procedimento de validação da Fase 3
└── scripts/smoke.sh                  # teste HTTP antes/depois (bash + curl)
```

| Área exigida | Arquivo | Conteúdo |
|---|---|---|
| Análise de projeto | `project-analysis.md` | Tabelas manifesto → linguagem, dependência → framework, sinais de banco, padrões de grep de rotas por framework (Flask, FastAPI, Express, Django, Spring, Go), perfil de execução e critérios para classificar a arquitetura |
| Catálogo de anti-patterns | `anti-patterns-catalog.md` | 22 anti-patterns (5 CRITICAL, 5 HIGH, 6 MEDIUM, 6 LOW) com regex de detecção, critério de confirmação, falsos positivos, regras de escalonamento e **recomendação padrão** (ex.: AP-04); tabela de **APIs deprecated** para Python, SQLAlchemy, Flask, Node, Express 5, Go, PHP e Java |
| Template de relatório | `audit-report-template.md` | Formato fixo (IDs `F-xx`, `File: arquivo:linhas`, ordenação, Summary com contagem de deprecated), regra de Recommendation executável e exemplos preenchidos |
| Guidelines de arquitetura | `mvc-guidelines.md` | Responsabilidades e proibições de cada camada, regra de dependência, estrutura-alvo por stack, estratégia para monolito × projeto parcialmente organizado, ordem de refatoração e **mudanças de contrato permitidas** |
| Playbook de refatoração | `refactoring-playbook.md` | 16 transformações (PB-01…PB-16) com código antes/depois em Python **e** JavaScript e como verificar cada uma |

### Decisões de design

1. **SKILL.md como orquestrador, referências como conhecimento.** O SKILL.md diz *o que* fazer e *quando* ler cada referência: a Fase 1 lê só a análise de projeto, a Fase 2 lê catálogo e template, a Fase 3 lê guidelines, playbook e validação. Isso mantém o contexto enxuto (carregamento progressivo).
2. **Fases 1 e 2 estritamente somente-leitura.** Nem a aplicação é executada antes da confirmação, porque subir o app cria arquivos (ex.: `loja.db`). A pergunta `[y/n]` encerra o turno sem nenhuma chamada de ferramenta posterior. A skill tem `disable-model-invocation: true`, então só roda quando invocada explicitamente.
3. **Evidência exata.** Cada finding exige arquivo:linha lido do arquivo real (Read/`grep -n`) e confirmação do sinal: regex sozinho não vira finding.
4. **A Recommendation é um contrato entre as fases.** Para CRITICAL/HIGH, a Fase 2 escreve a recomendação como lista de ações concretas, rota por rota e arquivo por arquivo, sem "avaliar" ou "em tarefa própria". A Fase 3 transforma cada recomendação em uma ação por localização (`F-02.1`, `F-02.2`…), aplica todas e confere cada uma no código. Um CRITICAL/HIGH só termina como `resolved`.
5. **Contrato HTTP como critério de "funciona".** Antes de alterar código, a Fase 3 grava um baseline do app original (todas as rotas, casos de sucesso e de erro) com `smoke.sh` e depois compara com o app refatorado. Só são aceitas as diferenças de "Mudanças de contrato permitidas": remover senha e segredo das respostas, exigir token nas rotas que um finding CRITICAL/HIGH manda proteger, remover endpoint de execução arbitrária, 500 → 400 em entrada inválida e ataque deixando de funcionar. Mudanças pedidas só por findings MEDIUM/LOW não podem alterar respostas de sucesso.
6. **Teste negativo de autenticação.** Toda rota protegida pela Fase 3 é chamada sem token (`requests-unauth.txt`) e precisa responder 401, ou 403 para campo de privilégio.
7. **Sem dependências novas.** Hash de senha e token assinado com o que já vem instalado (Werkzeug e itsdangerous no Flask; `crypto` no Node), conexão por requisição com `flask.g`, transações com `with conn:` / `BEGIN…COMMIT`.
8. **Artefatos auditáveis.** Tudo que a Fase 3 produz para validar fica em `.refactor-arch/` (relatório, requests, baseline, after, unauth, logs) e foi commitado como evidência.

### Anti-patterns do catálogo e por quê

| Severidade | Anti-patterns | Motivação |
|---|---|---|
| CRITICAL | Hardcoded secrets · SQL Injection · senha insegura/dados sensíveis expostos · endpoint perigoso sem proteção · God Class/Module | Encontrados nos 3 projetos (ex.: login sem senha via SQLi, `/admin/query` executando SQL arbitrário, hash MD5 devolvido pela API, chave `pk_live` e cartão em log) |
| HIGH | Regra de negócio em rota/controller · estado global mutável · fluxo multi-escrita sem transação · acoplamento sem DI · config de runtime insegura | Violações MVC/SOLID que impediam testar regras isoladamente (checkout em callback hell, conexão global compartilhada entre threads, debug + `0.0.0.0`) |
| MEDIUM | N+1 · duplicação/abstração ignorada · validação ausente · error handling espalhado · **APIs deprecated** · integridade referencial | Problemas reais nos 3 projetos; o P3 tinha `Task.is_overdue()` e constantes prontas que ninguém usava |
| LOW | Queries redundantes · magic numbers · nomes ruins · print como log · código morto · construções não idiomáticas | Qualidade/legibilidade |

Os sinais de detecção vieram diretamente da análise manual (tabela "Padrões transversais" da seção A): cada problema encontrado à mão virou um sinal genérico e acionável, por exemplo "query dentro de `for`/`forEach`" ou "literal atribuído a `*key*`/`*secret*`".

### Como a skill é agnóstica de tecnologia

- Detecção guiada por **tabelas de heurísticas** (manifestos, dependências, padrões de rota por framework), não por nomes de arquivos dos projetos.
- Regex do catálogo cobre sintaxes Python e JavaScript (f-string, concatenação, template literal; `print`/`console.log`; `except:`/callback sem `err`).
- Guidelines definem as camadas de forma abstrata e trazem a estrutura-alvo por stack (Flask, Express e mapeamento para FastAPI, Spring e Go).
- **Estratégia de adaptação**: monolito → criar a estrutura completa; projeto parcialmente organizado → preservar o que está adequado, adicionar o que falta, mover o que está fora do lugar e reaproveitar helpers existentes.
- Validação por HTTP (bash + curl), independente da linguagem.
- A mesma pasta é copiada sem alterações para os 3 projetos (`diff -r` idêntico).

### Desafios encontrados e como foram resolvidos

| Desafio | Solução |
|---|---|
| **Recomendações CRITICAL aplicadas pela metade** (avaliação técnica após a 1ª rodada): no P1 o F-02 mandava remover `POST /admin/query`, mas a rota só ganhou token; no P2 o F-03 mandava proteger as rotas destrutivas, mas só o relatório financeiro foi protegido e o `DELETE /api/users/:id` ficou aberto. A causa estava na skill: as guidelines proibiam "inventar autenticação" para rotas comuns e aceitavam o status `deferred` | A Recommendation de CRITICAL/HIGH virou escopo obrigatório da Fase 3 (desdobrada em uma ação por localização e verificada no código). O status `deferred` foi removido. AP-04 ganhou recomendação padrão: remover execução arbitrária, token em todas as rotas do finding, `role` só com token admin, token de login assinado. O PB-04 ganhou exemplos dessas transformações e a validação ganhou o teste negativo sem token. Os 3 projetos foram refatorados de novo a partir do código original |
| **Cascata apagando histórico financeiro** (P2, 1ª rodada): a skill corrigiu "dados órfãos" apagando matrículas **e pagamentos** junto com o usuário; o relatório financeiro passou de 997 para 0. A validação da própria skill não pegou porque não lia o relatório depois do delete | PB-16 passou a proibir cascata em registros financeiros/auditoria, e o guia de validação passou a exigir repetir leituras agregadas **após** deletes |
| **Processo órfão na porta 3000** (P2, 1ª rodada): o smoke chegou a medir o app errado | Guia de validação exige porta livre antes do boot, `setsid` (grupo de processos próprio), `kill` do grupo inteiro e confirmação de porta liberada |
| **Formato de datas** ao trocar `datetime.utcnow()` | Helper `utc_now()` em UTC *naive*: remove a deprecação sem mudar o texto das datas nas respostas nem comparar aware × naive |
| **Senhas já gravadas no formato antigo** (texto plano / MD5) | Migração transparente: no login (ou no boot, no P1) o hash legado é aceito uma vez e regravado com scrypt |
| **Formato de erro original** (`erro`, `error` ou texto puro) | O error handler central reproduz o formato do projeto, para não mudar o contrato |
| **Confirmação humana com execução não interativa** | Os runs foram feitos com `claude -p "/refactor-arch"`; o relatório foi revisado e a Fase 3 confirmada com `claude -p "y" --resume <sessão>` |

---

## C) Resultados

Resultados da execução final da skill (2ª rodada, após a correção das recomendações), a partir do código original de cada projeto.

### Resumo das auditorias

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Deprecated | Relatório |
|---|---|---|---|---|---|---|---|
| 1 — code-smells-project | 5 | 4 | 5 | 6 | 20 | nenhuma | [audit-project-1.md](reports/audit-project-1.md) |
| 2 — ecommerce-api-legacy | 4 | 3 | 4 | 5 | 16 | nenhuma | [audit-project-2.md](reports/audit-project-2.md) |
| 3 — task-manager-api | 3 | 2 | 7 | 6 | 18 | 2 (`datetime.utcnow()`, `Query.get()`) | [audit-project-3.md](reports/audit-project-3.md) |

Todos os problemas da análise manual foram encontrados (18/18, 16/16, 18/18; alguns agrupados num mesmo finding, por exemplo CORS dentro de "Insecure Runtime Configuration"). A skill também achou problemas que a análise manual não tinha visto: `card` numérico derrubando o processo no P2 e `?priority=abc` gerando 500 no P3. No P3, um finding MEDIUM (F-12, categoria órfã) se mostrou falso positivo na validação, porque o ORM já anulava o `category_id`; a Fase 3 registrou isso.

### Resolução dos findings

| Projeto | Ações CRITICAL/HIGH implementadas | Resolvidos | Parciais (só MEDIUM/LOW) |
|---|---|---|---|
| 1 | 33/33 | 18 | 2: validações que transformariam sucesso em erro; soft delete/404 que mudariam respostas de sucesso |
| 2 | 17/17 | 13 | 3: formato de e-mail; 404 para id inexistente no delete; `console` sem helper de logger |
| 3 | 17/17 | 17 | 1: validações que transformariam sucesso em erro |

### Estrutura antes × depois

**Projeto 1 — code-smells-project** (monolito → MVC completo)
```
ANTES (4 arquivos, ~780 linhas)          DEPOIS (25 arquivos, ~879 linhas)
app.py         rotas + admin + SQL       app.py                 composition root (create_app)
controllers.py HTTP + regras + SQL       config/settings.py     env vars
models.py      SQL + regras, 4 domínios  models/                database (conexão por request, migração de senhas),
database.py    conexão global + seed                            produto, usuario, pedido (transação, JOIN), sistema
                                         controllers/           produto, usuario, pedido, sistema, validation
                                         views/                 blueprints por domínio
                                         middlewares/           error_handler, auth (X-Admin-Token)
                                         services/              notification_service
                                         (POST /admin/query removido)
```

**Projeto 2 — ecommerce-api-legacy** (God Class → MVC em `src/`)
```
ANTES (3 arquivos, ~180 linhas)          DEPOIS (19 arquivos, ~355 linhas)
src/app.js         bootstrap             src/app.js            composition root (DI + listen)
src/AppManager.js  DB + schema + rotas   src/config/           process.env
                   + regras (God Class)  src/models/           database (promisificado, transação serializada),
src/utils.js       config com segredos                         user, course (JOIN), enrollment, payment, auditLog
                   + cache global        src/services/         checkout, report, user
                   + "badCrypto"         src/controllers/      checkout, report, user
                                         src/routes/           checkoutRoutes, adminRoutes, userRoutes (camada View)
                                         src/middlewares/      errorHandler (asyncHandler), auth
```

**Projeto 3 — task-manager-api** (parcialmente organizado → camadas completas, preservando o que existia)
```
ANTES (15 .py, ~1.155 linhas)            DEPOIS (28 .py, ~1.143 linhas)
app.py       config hardcoded            app.py              create_app()
models/      ORM (mantido)               config/settings.py  env vars + constantes de domínio
routes/      blueprints "gordos"         models/             ORM + regras (is_overdue, hash, migração MD5) + report.py
             (+ CRUD de categorias       controllers/        task, user, category, report, validation
              dentro de report_routes)   routes/             blueprints finos (category_routes e system_routes novos)
services/    NotificationService morto   middlewares/        error_handler, auth (token admin, token de login assinado)
utils/       helpers não usados          utils/              time.py (utc_now), helpers.py (só o que é usado)
                                         (services/ removido; marshmallow e requests removidos do requirements)
```

### Checklist de validação

| Item | P1 | P2 | P3 |
|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✅ | ✅ | ✅ |
| Framework detectado corretamente | ✅ Flask 3.1.1 | ✅ Express 4.18.2 | ✅ Flask 3.0.0 |
| Domínio descrito corretamente | ✅ | ✅ | ✅ Task Manager |
| Nº de arquivos condiz com a realidade | ✅ 4 | ✅ 3 | ✅ 12 (+3 `__init__` vazios excluídos por regra) |
| **Fase 2** — Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Findings ordenados CRITICAL → LOW | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 20 | ✅ 16 | ✅ 18 |
| Detecção de APIs deprecated | ✅ n/a (nenhuma) | ✅ n/a (nenhuma) | ✅ 2 |
| Pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3** — Estrutura segue padrão MVC | ✅ | ✅ | ✅ |
| Configuração extraída (sem hardcoded) | ✅ | ✅ | ✅ |
| Models criados para abstrair dados | ✅ | ✅ | ✅ |
| Views/Routes separadas | ✅ | ✅ | ✅ |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ `python app.py` | ✅ `npm start` | ✅ `python app.py` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem corretamente | ✅ | ✅ | ✅ |

### Validação (logs)

Além da validação feita pela própria skill, cada projeto refatorado foi conferido contra um **baseline independente**, capturado das aplicações originais antes da criação da skill (requisições com `X-Admin-Token`):

| Projeto | Validação da skill (`.refactor-arch/`) | Sem token (`unauth.txt`) | Baseline independente |
|---|---|---|---|
| 1 | 44/44 (42 iguais + 2 mudanças permitidas) | 5/5 → 401 | **31/32 status iguais**; a diferença é `POST /admin/query` 200 → 404 (removido) |
| 2 | 12/14 iguais; 2 = linhas após o crash do original (000 → 400/200) | 2/2 → 401 | **9/9 status iguais**; 8/9 corpos idênticos (1 difere só na ordem dos itens do relatório) |
| 3 | 61/61 (60 iguais + 1 500 → 400) | 3/3 → 401, 3/3 → 403 | **31/31 status iguais** |

Verificações adicionais executadas na aplicação refatorada:
- P1: `POST /admin/query` responde 404 mesmo com token e o path não existe mais no código; reset-db, `POST`/`PUT`/`DELETE /produtos` e `PUT /pedidos/<id>/status` sem token (ou com token errado) → 401; `GET /produtos` continua público; login com `admin@loja.com' --` → 401 e login do seed → 200.
- P2: relatório financeiro e `DELETE /api/users/:id` sem token ou com token errado → 401; `card` numérico → 400 (antes derrubava o processo); log sem número de cartão nem chave do gateway.
- P3: os 3 DELETE sem token → 401; `role: admin` sem token em `POST /users` e `role` em `PUT /users/2` → 403; `POST /users` comum → 201; login devolve token assinado (`eyJ1aWQiOjJ9…`); `python -W error::DeprecationWarning -c "import app"` sem avisos; hash MD5 legado migrado para scrypt no login.

Trechos dos logs de boot após a refatoração (`.refactor-arch/app-after.log`):

```
# code-smells-project
 * Debug mode: off
 * Running on http://127.0.0.1:5000

# ecommerce-api-legacy
LMS API rodando na porta 3000

# task-manager-api
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

Saída do teste sem token (P3, `.refactor-arch/unauth.txt`):
```
401 DELETE /tasks/1
401 DELETE /users/1
401 DELETE /categories/1
403 POST /users
403 PUT /users/2
403 PUT /users/2
```

### Mudanças de contrato intencionais

Todas exigidas por findings CRITICAL/HIGH ou por correção de erro 500:

| Projeto | Mudança |
|---|---|
| 1 | `POST /admin/query` removido (404) |
| 1 | `POST /admin/reset-db`, `POST /produtos`, `PUT/DELETE /produtos/<id>`, `PUT /pedidos/<id>/status` exigem `X-Admin-Token` (401 sem) |
| 1 | `senha` removida de `/usuarios`; `secret_key`, `debug` e `db_path` removidos de `/health`; CORS restrito a `CORS_ORIGINS` |
| 2 | `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem `X-Admin-Token` (401 sem) |
| 2 | checkout com pagamento recusado não cria mais o usuário; ordem dos itens do relatório agora determinística (por id) |
| 3 | `DELETE /tasks|users|categories/<id>` exigem `X-Admin-Token` (401 sem); `role`/`active` só com token (403 sem) |
| 3 | `password` removido das respostas; token de `/login` agora assinado (mesmo campo string); CORS restrito a `CORS_ORIGINS` |
| todos | entradas inválidas que davam 500 → 400; erros inesperados com mensagem genérica; servidor em `127.0.0.1` com debug desligado por padrão |

Caso de borda registrado pela Fase 3 no P3: `PUT` em id inexistente **sem** `Content-Type: application/json` passou a responder 415 em vez de 404, porque a rota lê o corpo antes de o controller buscar o registro.

### Comportamento da skill em stacks diferentes

- **Monolito Python (P1):** criou a estrutura MVC completa, separando por domínio e por camada, e removeu os arquivos originais e o endpoint de SQL arbitrário.
- **Node/Express (P2):** aplicou os mesmos padrões com idioma JavaScript: factories com injeção de dependência, wrapper promisificado do sqlite3, `async/await` no lugar do callback hell, `asyncHandler` para o Express 4 e transações serializadas na conexão única. Também criou uma camada de services para os casos de uso.
- **Python parcialmente organizado (P3):** reconheceu a arquitetura como "parcialmente em camadas", manteve `models/` e os blueprints (`routes/` documentado como camada View), adicionou só o que faltava e reaproveitou `Task.is_overdue()`, `validate_email` e `calculate_percentage`, que estavam ignorados.
- Nos 3 casos, a skill parou corretamente na confirmação e implementou todas as ações CRITICAL/HIGH do próprio relatório.

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado.
- Python 3.12+ (testado com 3.13) e Node.js 18+ (testado com 22).
- `bash` e `curl` (usados por `scripts/smoke.sh`).

### Executar a skill

Ordem sugerida: P1 (monolito, calibra a skill) → P2 (outra stack) → P3 (projeto parcialmente organizado).

```bash
cd code-smells-project      && claude "/refactor-arch"
cd ../ecommerce-api-legacy  && claude "/refactor-arch"
cd ../task-manager-api      && claude "/refactor-arch"
```

A skill imprime a análise (Fase 1) e o relatório (Fase 2), e para em `Proceed with refactoring (Phase 3)? [y/n]`. Responda `y` para refatorar. O relatório fica salvo em `.refactor-arch/audit-report.md`; copie-o para `reports/audit-project-N.md`.

Para rodar novamente sobre o código original, use uma cópia limpa do commit original e copie a skill para ela:

```bash
git worktree add ../original 6d1ce62
cp -r code-smells-project/.claude ../original/code-smells-project/
cd ../original/code-smells-project && claude "/refactor-arch"
```

### Rodar as aplicações refatoradas

```bash
# Projeto 1
cd code-smells-project && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ADMIN_TOKEN=troque-me .venv/bin/python app.py            # http://127.0.0.1:5000

# Projeto 2
cd ecommerce-api-legacy && npm install
ADMIN_TOKEN=troque-me npm start                          # http://localhost:3000

# Projeto 3
cd task-manager-api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python seed.py && ADMIN_TOKEN=troque-me .venv/bin/python app.py   # http://127.0.0.1:5000
```

Rotas administrativas e destrutivas exigem o header `X-Admin-Token: <ADMIN_TOKEN>`; sem `ADMIN_TOKEN` configurado, elas respondem 401. Variáveis disponíveis em cada `.env.example` (`SECRET_KEY`, `ADMIN_TOKEN`, `HOST`, `PORT`, `CORS_ORIGINS`, …).

### Validar que a refatoração funcionou

Com a aplicação rodando, repita as requisições gravadas pela skill e compare com o baseline do código original:

```bash
cd code-smells-project
S=.claude/skills/refactor-arch/scripts/smoke.sh
bash $S http://localhost:5000 .refactor-arch/requests.txt /tmp/after.txt "X-Admin-Token: $ADMIN_TOKEN"
diff .refactor-arch/baseline.txt /tmp/after.txt          # só as mudanças intencionais devem aparecer
bash $S http://localhost:5000 .refactor-arch/requests-unauth.txt /tmp/unauth.txt   # todas devem dar 401/403
```

Partir de um banco recém-criado (P1: remover `loja.db`; P3: `python seed.py`) para que os IDs coincidam com os do baseline.
