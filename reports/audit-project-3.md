================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.13 + Flask 3.0.0 (SQLite via Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.1.9)
Files:   12 analyzed | ~1155 lines of code

## Summary
CRITICAL: 3 | HIGH: 2 | MEDIUM: 7 | LOW: 6
Deprecated APIs: 2 detected (F-06, F-09)

## Findings

### F-01 [CRITICAL] Hardcoded Credentials / Secrets
Anti-pattern: AP-01
File: app.py:13; services/notification_service.py:7-10
Description: SECRET_KEY literal ('super-secret-key-123') em app.config e credenciais SMTP literais (email_user 'taskmanager@gmail.com', email_password 'senha123') no construtor de NotificationService.
Impact: Quem tem acesso ao repositório pode forjar sessões/tokens assinados com a SECRET_KEY e usar a conta de e-mail; segredos ficam no histórico do git.
Recommendation: (1) Criar config/settings.py que lê SECRET_KEY do ambiente (fallback aleatório por processo com secrets.token_hex quando ausente) e aplicá-lo em app.py:13; (2) eliminar as credenciais SMTP literais de services/notification_service.py:7-10 removendo o serviço, que não é usado por nenhuma rota (ver F-13); (3) documentar as variáveis em .env.example (PB-01).

### F-02 [CRITICAL] Insecure Password Storage / Sensitive Data Exposure
Anti-pattern: AP-03
File: models/user.py:21, 27-32; routes/user_routes.py:33, 85, 129, 209
Description: Senhas guardadas como MD5 sem salt (hashlib.md5 em set_password/check_password) e o hash é serializado em User.to_dict() ('password': self.password), que vai para as respostas de GET /users/<id>, POST /users, PUT /users/<id> e POST /login.
Impact: Um hash MD5 vazado é revertido em segundos com rainbow tables. Qualquer cliente lê o hash de qualquer usuário.
Recommendation: (1) Trocar set_password/check_password por werkzeug.security.generate_password_hash/check_password_hash (já instalado com o Flask), aceitando hashes MD5 legados só para verificar e regravando-os no novo formato após login bem-sucedido; (2) remover 'password' de User.to_dict(), o que tira o campo das respostas em routes/user_routes.py:33, 85, 129, 209 (PB-03).

### F-03 [CRITICAL] Unprotected Dangerous Endpoint
Anti-pattern: AP-04
File: routes/report_routes.py:211-223; routes/task_routes.py:225-238; routes/user_routes.py:52, 71-72, 78, 119-125, 134-151, 210
Description: DELETE /categories/<id>, DELETE /tasks/<id> e DELETE /users/<id> apagam dados (inclusive dados pessoais e as tasks em cascata) sem autenticação. POST /users e PUT /users/<id> aceitam 'role' (e 'active') vindos do cliente. POST /login devolve um token previsível 'fake-jwt-token-' + str(user.id).
Impact: Qualquer cliente anônimo apaga usuários, tasks e categorias, se cadastra como admin ou desativa outras contas, e forja o token de qualquer usuário trocando o id.
Recommendation: (1) Exigir X-Admin-Token (= ADMIN_TOKEN da config, comparação com hmac.compare_digest) em DELETE /categories/<id>, DELETE /tasks/<id> e DELETE /users/<id> → 401 sem token válido; (2) aceitar os campos de privilégio 'role' (POST /users, PUT /users/<id>) e 'active' (PUT /users/<id>) só com X-Admin-Token válido, senão 403; (3) trocar o token de POST /login por um token assinado com SECRET_KEY via itsdangerous.URLSafeTimedSerializer, mantendo o campo 'token' como string (PB-04).

### F-04 [HIGH] Insecure Runtime Configuration
Anti-pattern: AP-10
File: app.py:15, 34
Description: app.run(debug=True, host='0.0.0.0', port=5000) fixo no código e CORS(app) liberado para qualquer origem.
Impact: O debugger do Werkzeug exposto na rede permite executar código remotamente. Qualquer site pode chamar a API pelo navegador da vítima.
Recommendation: (1) Ler DEBUG (padrão False), HOST (padrão 127.0.0.1) e PORT (padrão 5000) de config/settings.py e usá-los em app.run (app.py:34); (2) restringir o CORS às origens de CORS_ORIGINS da config (app.py:15) (PB-01).

### F-05 [HIGH] Business Logic in Route (Fat Controller)
Anti-pattern: AP-06
File: routes/report_routes.py:12-101, 103-155, 157-223; routes/task_routes.py:11-63, 65-83, 85-154, 156-223, 225-238, 240-271, 273-299; routes/user_routes.py:10-25, 27-40, 42-90, 92-132, 134-151, 153-183, 185-211
Description: Todos os handlers consultam o banco direto (Model.query, db.session), validam com listas literais, calculam atraso, estatísticas e completion_rate, e serializam dicts à mão. O CRUD de categorias está dentro do blueprint de relatórios.
Impact: Nenhuma regra pode ser testada sem HTTP. Mudar uma regra (ex.: o que conta como "atrasada") exige editar 6 lugares. A coesão dos módulos é baixa.
Recommendation: (1) Criar controllers/ (task_controller, user_controller, category_controller, report_controller) que orquestram cada caso de uso de todas as rotas listadas; (2) levar queries, agregações e regras (is_overdue, estatísticas, validação de domínio) para os models; (3) deixar routes/*.py só mapeando HTTP → controller; (4) mover o CRUD de categorias de routes/report_routes.py:157-223 para routes/category_routes.py (PB-06, PB-14).

### F-06 [MEDIUM] Deprecated API: datetime.utcnow()
Anti-pattern: AP-15
File: models/category.py:11; models/task.py:15-16, 52; models/user.py:14; routes/report_routes.py:35, 42, 45, 71, 133; routes/task_routes.py:31, 72, 215, 285; routes/user_routes.py:172; services/notification_service.py:35; utils/helpers.py:38; seed.py:66-67, 69-70, 74
Description: datetime.utcnow está deprecated desde o Python 3.12 (o ambiente roda 3.13.5) e emite DeprecationWarning.
Impact: Vai quebrar quando for removido. Também devolve datetime naive, sujeito a erros de fuso.
Recommendation: Substituir por um helper utc_now() centralizado em utils/time.py, baseado em datetime.now(timezone.utc), mantendo valores naive em UTC para não mudar o formato gravado e serializado (PB-13).

### F-07 [MEDIUM] Duplicated Logic / Ignored Existing Abstraction
Anti-pattern: AP-12
File: models/task.py:38-60; routes/report_routes.py:7, 19-22, 34-36, 67, 132-135, 151; routes/task_routes.py:17-28, 30-39, 71-80, 110, 177, 276-279, 284-287, 296; routes/user_routes.py:61, 71, 106, 120, 171-180; utils/helpers.py:19-23, 57-108, 110-116
Description: O cálculo de "atrasada" aparece 6 vezes, mas Task.is_overdue (models/task.py:50-60) nunca é usado. A serialização de task (task_routes.py:17-28) repete Task.to_dict. A lista de status e a de roles são literais repetidos, enquanto Task.validate_status, VALID_STATUSES e VALID_ROLES ficam sem uso. A regex de e-mail repete validate_email. completion_rate repete calculate_percentage (importado e não usado). process_task_data não é usado.
Impact: Regras divergem com o tempo (create e update já validam título de formas diferentes); correções precisam ser replicadas.
Recommendation: Centralizar em um ponto só (Task.is_overdue, Task.to_dict, constantes de domínio, validate_email, calculate_percentage) e remover as cópias (PB-10).

### F-08 [MEDIUM] N+1 Queries
Anti-pattern: AP-11
File: routes/report_routes.py:55-56, 163; routes/task_routes.py:41-57; routes/user_routes.py:22
Description: GET /tasks roda User.query.get e Category.query.get para cada task. GET /users carrega u.tasks (lazy) para cada usuário. /reports/summary consulta as tasks de cada usuário. GET /categories faz um count por categoria.
Impact: O número de queries cresce linearmente com os registros e a latência degrada com volume.
Recommendation: Usar joinedload/selectinload nos relacionamentos e agregações com GROUP BY (func.count) (PB-09).

### F-09 [MEDIUM] Deprecated API: Query.get()
Anti-pattern: AP-15
File: routes/report_routes.py:105, 192, 213; routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227; routes/user_routes.py:29, 94, 136, 155
Description: Model.query.get(id) é API legada no SQLAlchemy 2.x (LegacyAPIWarning).
Impact: Vai quebrar em versão futura e gera warnings em runtime.
Recommendation: Substituir por db.session.get(Model, id) dentro dos models/controllers (PB-13).

### F-10 [MEDIUM] Missing Input Validation
Anti-pattern: AP-13
File: routes/report_routes.py:173-180, 196-202; routes/task_routes.py:92-100, 113, 166-171, 181-184, 260-264; routes/user_routes.py:102-103, 124-125
Description: PUT /categories/<id> sem corpo JSON faz 'name' in None (TypeError → 500). 'priority' é comparado sem conversão ('alta' < 1 → TypeError → 500). Um título não-string quebra len(). int(request.args['priority']) com valor inválido dá ValueError → 500. Color não é validado (is_valid_color não é usado). Nome de usuário pode virar vazio no update. 'active' aceita qualquer tipo.
Impact: Entrada inválida derruba a requisição com 500 em vez de 400 e dados inconsistentes entram no banco.
Recommendation: Validar presença, tipo e faixa na borda (controller), com as mesmas regras para create e update, respondendo 400 com mensagem (PB-11).

### F-11 [MEDIUM] Scattered or Swallowed Error Handling
Anti-pattern: AP-14
File: routes/report_routes.py:186-188, 207-209, 221-223; routes/task_routes.py:62-63, 137, 151-154, 204, 221-223, 236-238; routes/user_routes.py:87-90, 130-132, 149-151; services/notification_service.py:23-25; utils/helpers.py:46, 49, 88
Description: Há bare except: e try/except replicado em cada handler, str(e) só em print, e nenhum error handler central (404/405/500 sem JSON padronizado).
Impact: Erros reais (inclusive bugs de programação) somem sem log útil; o comportamento varia entre endpoints.
Recommendation: Registrar error handlers centrais em middlewares/error_handler.py (rollback + log + JSON {'error': ...}) e capturar só exceções específicas (ValueError, SQLAlchemyError) (PB-12).

### F-12 [MEDIUM] Broken Referential Integrity on Delete
Anti-pattern: AP-16
File: routes/report_routes.py:211-223
Description: DELETE /categories/<id> remove a categoria sem tratar tasks.category_id, que continua apontando para o id apagado (o SQLite não aplica FK por padrão).
Impact: Ficam tasks órfãs com category_id inválido, e um novo registro pode reutilizar o id.
Recommendation: Na mesma transação da exclusão, desassociar as tasks da categoria (category_id = NULL) (PB-16).

### F-13 [LOW] Dead Code / Unused Imports
Anti-pattern: AP-21
File: app.py:7; models/task.py:3; routes/report_routes.py:7-8; routes/task_routes.py:7; routes/user_routes.py:6; services/notification_service.py:1-48; utils/helpers.py:3-7, 9-12, 25-34, 36-41
Description: Imports sem uso (os, sys, json, time, hashlib, format_date, calculate_percentage). NotificationService não é instanciado em lugar nenhum. format_date, sanitize_string, generate_id e log_action não têm referências. requirements.txt declara marshmallow, requests e python-dotenv, que não são usados.
Impact: Ruído, superfície de manutenção maior e falsa impressão de funcionalidades existentes.
Recommendation: Remover imports, funções e o serviço não usados (helpers reaproveitáveis entram via F-07) (PB-15).

### F-14 [LOW] Poor Naming
Anti-pattern: AP-19
File: models/category.py:14; routes/report_routes.py:24-28, 55, 159-161; routes/task_routes.py:16, 51; routes/user_routes.py:14; seed.py:16-61, 78
Description: Identificadores como d, t, u, c, cat, td, p1 a p5, u1 a u3 e c1 a c4.
Impact: Leitura mais lenta e propensa a erro.
Recommendation: Usar nomes descritivos (task, user, category, priority_counts) (PB-15).

### F-15 [LOW] Non-idiomatic Constructs
Anti-pattern: AP-22
File: models/task.py:39-43, 46-48, 50-60; models/user.py:35-38; routes/task_routes.py:141, 210; utils/helpers.py:21-23, 53-55, 103
Description: if cond: return True else: return False, type(x) == list e if aninhados em 3 níveis para uma condição booleana.
Impact: Código prolixo e mais difícil de ler.
Recommendation: Retornar a expressão booleana direto, usar isinstance e achatar as condições (PB-15).

### F-16 [LOW] Redundant Queries
Anti-pattern: AP-17
File: routes/report_routes.py:15-28; routes/task_routes.py:275-279
Description: 4 COUNTs separados por status e 5 COUNTs por prioridade sobre a tabela tasks.
Impact: Várias idas ao banco onde uma query com GROUP BY basta.
Recommendation: Agregar com uma query GROUP BY status e outra GROUP BY priority no model (PB-09).

### F-17 [LOW] Magic Numbers / Strings
Anti-pattern: AP-18
File: routes/report_routes.py:45, 129, 180; routes/task_routes.py:96, 99, 104, 113; routes/user_routes.py:52, 64, 115
Description: Valores literais de regra de negócio: 3 e 200 (título), 1 e 5 (prioridade), padrão 3, <= 2 ("alta prioridade"), 7 dias, '#000000', 4 (senha), 'user'. As constantes de utils/helpers.py:110-116 existem e não são usadas.
Impact: Mudar uma regra exige caçar literais pelo código.
Recommendation: Usar constantes de domínio nomeadas num único módulo (PB-15).

### F-18 [LOW] Print as Logging
Anti-pattern: AP-20
File: routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; services/notification_service.py:21, 24; utils/helpers.py:39, 41
Description: Eventos e erros da aplicação registrados com print().
Impact: Sem níveis, timestamp ou destino configurável, então não dá para filtrar em produção.
Recommendation: Usar logging.getLogger(__name__) com níveis adequados (o print do CLI seed.py é aceitável) (PB-15).

================================
Total: 18 findings
================================
