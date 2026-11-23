================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (SQLite via Flask-SQLAlchemy 3.1.1)
Files:   12 analyzed | ~1155 lines of code

## Summary
CRITICAL: 2 | HIGH: 3 | MEDIUM: 7 | LOW: 6
Deprecated APIs: 2 detected (F-06, F-10)

## Findings

### F-01 [CRITICAL] Hardcoded Credentials / Secrets
Anti-pattern: AP-01
File: app.py:13; services/notification_service.py:9-10
Description: SECRET_KEY literal ('super-secret-key-123') na configuração do app e credenciais SMTP literais (email_user 'taskmanager@gmail.com', email_password 'senha123') no construtor do NotificationService.
Impact: Qualquer pessoa com acesso ao repositório obtém a chave de assinatura do Flask e a senha da conta de e-mail; rotacionar exige alterar código e fazer deploy.
Recommendation: Ler SECRET_KEY e credenciais SMTP de variáveis de ambiente em um módulo de configuração central, sem valores secretos versionados (PB-01).

### F-02 [CRITICAL] Insecure Password Storage / Sensitive Data Exposure
Anti-pattern: AP-03
File: models/user.py:21, 29, 32; routes/user_routes.py:33, 85, 129, 209
Description: Senhas armazenadas com hashlib.md5 sem salt (set_password/check_password) e o hash é serializado por User.to_dict() ('password': self.password), devolvido em GET /users/<id>, POST /users, PUT /users/<id> e POST /login.
Impact: Qualquer cliente lê os hashes MD5 pela API, e eles são quebráveis em segundos com rainbow tables (senhas do seed: '1234', 'abcd', 'pass'). Vazamento direto de credenciais.
Recommendation: Usar werkzeug.security.generate_password_hash/check_password_hash (já instalado com o Flask), com verificação compatível para hashes MD5 legados, e remover 'password' da serialização (PB-03).

### F-03 [HIGH] Insecure Runtime Configuration
Anti-pattern: AP-10
File: app.py:15, 34
Description: app.run(debug=True, host='0.0.0.0') fixos no código e CORS(app) sem restrição de origem.
Impact: Com debug ativo e bind em todas as interfaces, qualquer exceção expõe o debugger interativo do Werkzeug (execução remota de código) para a rede; o CORS aberto permite chamadas de qualquer origem.
Recommendation: Ler DEBUG/HOST/PORT/CORS_ORIGINS do ambiente com padrões seguros (debug desligado, 127.0.0.1) no módulo de config (PB-01).

### F-04 [HIGH] Business Logic in Controller/Route (Fat Controller)
Anti-pattern: AP-06
File: routes/report_routes.py:12-101, 103-155, 157-223; routes/task_routes.py:11-63, 85-154, 156-223, 240-271, 273-299; routes/user_routes.py:10-25, 42-90, 92-132, 134-151, 153-183, 185-211
Description: Os handlers fazem queries (Task.query, db.session), validações de regra (status, prioridade, roles, unicidade de e-mail), cálculos (overdue, completion_rate, days_overdue), agregações de relatório e serialização manual. O CRUD de categorias está no blueprint de relatórios.
Impact: Não dá para testar regras sem HTTP; a mesma regra é reescrita em vários handlers e diverge (ex.: create valida título e o update valida diferente); mudar o schema exige mexer em todas as rotas.
Recommendation: Rotas finas que só traduzem HTTP para controllers/services; regras e queries em services por domínio (tasks, users, categories, reports), validação em um módulo próprio; mover categorias para um blueprint próprio mantendo os paths (PB-06, PB-14).

### F-05 [HIGH] Unprotected Dangerous Endpoint
Anti-pattern: AP-04
File: routes/report_routes.py:211-223; routes/task_routes.py:225-238; routes/user_routes.py:52, 71-72, 119-122, 134-151, 207-211
Description: DELETE /tasks/<id>, DELETE /users/<id> (que também apaga todas as tasks do usuário) e DELETE /categories/<id> não exigem autenticação. POST /users e PUT /users/<id> aceitam 'role': 'admin' de qualquer cliente. O /login devolve um token previsível ('fake-jwt-token-' + id) que nenhuma rota verifica.
Impact: Qualquer cliente anônimo apaga dados, promove-se a admin ou desativa usuários; o "token" não oferece proteção.
Recommendation: Introduzir autenticação real (token assinado) e autorização por role nas rotas destrutivas/administrativas (PB-04). Exige mudança de contrato (401/403 para clientes sem token).

### F-06 [MEDIUM] Deprecated API: datetime.utcnow()
Anti-pattern: AP-15
File: models/category.py:11; models/task.py:15-16, 52; models/user.py:14; routes/report_routes.py:35, 42, 45, 71, 133; routes/task_routes.py:31, 72, 215, 285; routes/user_routes.py:172; seed.py:66-67, 69-70, 74; services/notification_service.py:35; utils/helpers.py:38
Description: datetime.utcnow() está deprecated desde o Python 3.12 (o interpretador é o 3.13.5) e emite DeprecationWarning.
Impact: Será removido em versões futuras; retorna datetime naive, sujeito a erros de fuso ao misturar com valores aware.
Recommendation: Centralizar em um helper utc_now() baseado em datetime.now(timezone.utc), normalizado para naive UTC para manter o formato atual das respostas e a comparação com colunas existentes (PB-13).

### F-07 [MEDIUM] Broken Referential Integrity on Delete
Anti-pattern: AP-16
File: models/task.py:13-14, 20-21; routes/report_routes.py:211-223
Description: DELETE /categories/<id> remove a categoria sem tratar as tasks que a referenciam. O SQLite não aplica FKs por padrão e o relationship não define cascade/ondelete.
Impact: As tasks ficam com category_id apontando para registro inexistente (category_name None em GET /tasks, mas category_id preenchido), o que gera dados inconsistentes nos relatórios.
Recommendation: Desvincular as tasks (category_id = None) na mesma transação da remoção da categoria, dentro do service (PB-16).

### F-08 [MEDIUM] Duplicated Logic / Ignored Existing Abstraction
Anti-pattern: AP-12
File: models/task.py:23-36, 39, 50-60; routes/report_routes.py:34-36, 67, 132-135, 151; routes/task_routes.py:17-28, 30-39, 71-80, 96-100, 110, 140-144, 167-170, 177, 209-213, 283-287, 296; routes/user_routes.py:61, 71, 106, 120, 162-180; utils/helpers.py:14-17, 21, 64, 75, 101-106, 110-111
Description: O cálculo de "overdue" está reescrito em 6 lugares, enquanto Task.is_overdue() existe e não é usado. A serialização de task é duplicada (task_routes.py:17-28 replica Task.to_dict). As listas de status/roles são literais em 2–3 lugares, apesar de VALID_STATUSES/VALID_ROLES existirem. A regex de e-mail é duplicada, apesar de validate_email existir. A validação de título e a normalização de tags aparecem em create, update e process_task_data, e completion_rate é calculado inline, apesar de calculate_percentage existir.
Impact: Mudar uma regra (ex.: novo status) exige editar vários arquivos; as cópias já divergem (mensagens de erro diferentes no create e no update).
Recommendation: Uma única fonte por regra: Task.is_overdue/to_dict no model, constantes de domínio em um módulo, validação compartilhada entre create/update e helper de percentual (PB-10).

### F-09 [MEDIUM] N+1 Queries
Anti-pattern: AP-11
File: routes/report_routes.py:53-56, 159-163; routes/task_routes.py:41-57; routes/user_routes.py:12-22
Description: GET /tasks executa User.query.get e Category.query.get para cada task. /reports/summary faz uma query de tasks por usuário. GET /categories faz um count por categoria. GET /users carrega u.tasks (lazy) por usuário.
Impact: O número de queries cresce linearmente com os registros (1 + 2N em /tasks), degradando a latência conforme a base cresce.
Recommendation: Usar eager loading (joinedload/selectinload) ou agregação com GROUP BY em uma única query (PB-09).

### F-10 [MEDIUM] Deprecated API: Query.get()
Anti-pattern: AP-15
File: routes/report_routes.py:105, 192, 213; routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227; routes/user_routes.py:29, 94, 136, 155
Description: Model.query.get(id) é API legacy no SQLAlchemy 2.x (exigido pelo Flask-SQLAlchemy 3.1.1) e emite LegacyAPIWarning.
Impact: Será removida em versões futuras do SQLAlchemy e gera ruído de warnings.
Recommendation: Substituir por db.session.get(Model, id) (PB-13).

### F-11 [MEDIUM] Missing Input Validation
Anti-pattern: AP-13
File: routes/report_routes.py:173-180, 196-202; routes/task_routes.py:92-100, 104, 113, 166-170, 181-184, 260-264; routes/user_routes.py:102-103, 105-106, 114-115, 124-125
Description: Os tipos não são verificados: 'priority' string ('5' < 1) e 'title' numérico em POST/PUT /tasks lançam TypeError; GET /tasks/search?priority=abc lança ValueError em int(). PUT /categories não checa body nulo ('name' in None). Em PUT /users, e-mail/senha não-string quebram re.match/len, 'name' vazio é aceito e 'active' aceita qualquer tipo. Color de categoria não é validado.
Impact: Entradas inválidas resultam em 500 (com debug ligado, página do debugger) em vez de 400, e dados inválidos são persistidos.
Recommendation: Validar presença, tipo, faixa e formato em uma camada de validação compartilhada, respondendo 400 com as mensagens existentes (PB-11).

### F-12 [MEDIUM] Scattered or Swallowed Error Handling
Anti-pattern: AP-14
File: routes/report_routes.py:186-188, 207-209, 221-223; routes/task_routes.py:62-63, 137-138, 151-154, 204-205, 221-223, 236-238; routes/user_routes.py:87-90, 130-132, 149-151; services/notification_service.py:23-25; utils/helpers.py:46, 49, 88
Description: Há try/except replicado em cada handler, vários "except:" sem tipo (engolem até KeyboardInterrupt/SystemExit), e GET /tasks envolve o handler inteiro em um except que esconde qualquer bug. Não existe error handler central.
Impact: Falhas reais são mascaradas sem log útil, e o comportamento de erro varia entre endpoints.
Recommendation: Exceções de domínio (NotFound/Validation/Conflict) e errorhandlers centrais no app com rollback e logging; exceptions específicas no parsing de datas (PB-12).

### F-13 [LOW] Dead Code / Unused Imports
Anti-pattern: AP-21
File: app.py:7; models/task.py:3, 38-48; models/user.py:34-38; routes/report_routes.py:7-8; routes/task_routes.py:7; routes/user_routes.py:6; services/notification_service.py:1-48; utils/helpers.py:3-7, 9-116
Description: Há imports não usados (os, sys, json em app.py; json, os, sys, time em task_routes; hashlib, json em user_routes; format_date, calculate_percentage, json em report_routes; json em models/task; os, json, sys, math, hashlib em helpers). Task.validate_status/validate_priority e User.is_admin nunca são chamados. NotificationService nunca é importado e nenhuma função/constante de utils/helpers.py é usada.
Impact: Ruído que confunde o leitor sobre o que está ativo e mantém credenciais (F-01) em código morto.
Recommendation: Remover imports e código não usados, reaproveitando o que fizer sentido (constantes/validadores) na nova estrutura (PB-15).

### F-14 [LOW] Non-idiomatic Constructs
Anti-pattern: AP-22
File: models/task.py:40-43, 46-48, 51-60; models/user.py:35-38; routes/task_routes.py:141, 210; utils/helpers.py:22-23, 53-55, 103
Description: Padrão "if cond: return True else: return False", ifs aninhados em 3 níveis em is_overdue e type(x) == list em vez de isinstance.
Impact: Código mais longo e difícil de ler; type() == falha com subclasses.
Recommendation: Retornar a expressão booleana diretamente, achatar condicionais e usar isinstance (PB-15).

### F-15 [LOW] Poor Naming
Anti-pattern: AP-19
File: models/task.py:45; models/user.py:27, 31; routes/report_routes.py:24-28; utils/helpers.py:25
Description: Parâmetros 'p', 'pwd' e 's' e variáveis com sufixo numérico p1..p5 para contagens por prioridade.
Impact: O significado precisa ser inferido do contexto; p1..p5 escondem o mapeamento prioridade→rótulo (critical..minimal).
Recommendation: Nomes descritivos (priority, password) e um mapeamento nomeado prioridade→rótulo (PB-15).

### F-16 [LOW] Redundant Queries
Anti-pattern: AP-17
File: routes/report_routes.py:15-28; routes/task_routes.py:275-279
Description: São 4 consultas COUNT por status e 5 por prioridade em sequência, sobre a mesma tabela tasks.
Impact: 9+ round-trips ao banco por chamada de relatório, quando um GROUP BY resolveria.
Recommendation: Agregar com GROUP BY status/priority em uma query cada (PB-09).

### F-17 [LOW] Magic Numbers / Strings
Anti-pattern: AP-18
File: routes/report_routes.py:24-28, 45, 129; routes/task_routes.py:96, 99, 104, 113, 167, 169, 182; routes/user_routes.py:64, 115
Description: Literais de regra sem nome: limites de título 3/200, faixa de prioridade 1–5, prioridade padrão 3, "alta prioridade" <= 2, janela de 7 dias, senha mínima de 4.
Impact: Alterar uma regra exige caçar literais, com risco de inconsistência.
Recommendation: Constantes nomeadas em um único módulo de domínio (PB-15).

### F-18 [LOW] Print/Console as Logging
Anti-pattern: AP-20
File: routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; services/notification_service.py:21, 24; utils/helpers.py:39, 41
Description: Eventos e erros da aplicação registrados com print().
Impact: Sem níveis, timestamps ou destino configurável; os erros se perdem em produção.
Recommendation: Usar o módulo logging (logger por módulo) (PB-15).

================================
Total: 18 findings
================================
