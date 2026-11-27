================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.13 + Flask 3.1.1 (SQLite)
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 5 | HIGH: 4 | MEDIUM: 5 | LOW: 6
Deprecated APIs: none detected for Python 3.13 + Flask 3.1.1

## Findings

### F-01 [CRITICAL] Hardcoded Credentials / Secrets
Anti-pattern: AP-01
File: app.py:7; controllers.py:286-289
Description: SECRET_KEY literal "minha-chave-super-secreta-123" em app.config, e o mesmo valor é devolvido no JSON de GET /health junto com "debug": True e "db_path": "loja.db".
Impact: Qualquer cliente anônimo obtém a chave de assinatura da aplicação via /health e pode forjar sessões e tokens. A chave também fica versionada no git.
Recommendation: (1) Ler SECRET_KEY de os.environ em config/settings.py, com fallback secrets.token_hex(32) gerado no boot (nunca literal), e remover o literal de app.py:7; (2) remover os campos secret_key, debug e db_path da resposta de GET /health (controllers.py:287-289) (PB-01).

### F-02 [CRITICAL] Unprotected Dangerous Endpoint
Anti-pattern: AP-04
File: app.py:14, 15, 16, 26, 47-57, 59-78
Description: POST /admin/query executa o SQL recebido em dados["sql"] (cursor.execute(query)). POST /admin/reset-db apaga as 4 tabelas. POST /produtos, PUT /produtos/<id>, DELETE /produtos/<id> e PUT /pedidos/<id>/status alteram catálogo, preços e status financeiro dos pedidos. Nenhuma dessas rotas tem autenticação.
Impact: Um cliente anônimo pode ler e alterar o banco inteiro (incluindo senhas), apagar todos os dados, zerar preços, remover produtos e aprovar ou cancelar pedidos de terceiros.
Recommendation: (1) Remover POST /admin/query e o handler executar_query (a rota passa a responder 404); (2) exigir o header X-Admin-Token igual a ADMIN_TOKEN da config (comparação com hmac.compare_digest) em POST /admin/reset-db, POST /produtos, PUT /produtos/<id>, DELETE /produtos/<id> e PUT /pedidos/<id>/status, respondendo 401 sem token válido (PB-04).

### F-03 [CRITICAL] God Module
Anti-pattern: AP-05
File: controllers.py:1-292; models.py:1-314
Description: models.py concentra o acesso a dados de produtos, usuários e pedidos mais regras de negócio (validação de estoque, cálculo de total, faixas de desconto). controllers.py concentra os handlers dos 3 domínios mais SQL direto (health_check) e efeitos colaterais (notificações). app.py mistura configuração, roteamento e SQL inline.
Impact: Qualquer mudança toca arquivos que atendem todos os domínios. Não dá para testar as camadas isoladamente e o risco de regressão cruzada é alto.
Recommendation: Dividir por camada e domínio (PB-05): config/settings.py; models/{database,produto_model,usuario_model,pedido_model,sistema_model}.py (SQL e regras de dados); controllers/{produto,usuario,pedido,sistema}_controller.py (orquestração); views/{produto,usuario,pedido,sistema}_routes.py (Blueprints); services/notification_service.py; middlewares/{auth,error_handler}.py; app.py apenas com create_app(). Remover os arquivos monolíticos controllers.py e models.py e o SQL inline de app.py.

### F-04 [CRITICAL] Insecure Password Storage / Sensitive Data Exposure
Anti-pattern: AP-03
File: database.py:76-78; models.py:83, 99, 109-111, 126-129
Description: As senhas são gravadas em texto plano no seed e em criar_usuario, comparadas em texto plano no login (WHERE senha = '...') e devolvidas no campo "senha" por GET /usuarios e GET /usuarios/<id>.
Impact: Qualquer cliente lista as senhas de todos os usuários, inclusive admin123 do administrador. Um vazamento do loja.db expõe as credenciais diretamente.
Recommendation: (1) Gravar a senha com werkzeug.security.generate_password_hash em criar_usuario e no seed; (2) no login, buscar por email com parâmetro e validar com check_password_hash; (3) remover "senha" da serialização de GET /usuarios e GET /usuarios/<id> (models.py:83, 99); (4) migrar no boot as senhas em texto plano já gravadas em loja.db para hash, sem perder usuários (PB-03).

### F-05 [CRITICAL] SQL Injection
Anti-pattern: AP-02
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-297; app.py:69
Description: As queries são montadas por concatenação com valores do request, por exemplo "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'" e "nome LIKE '%" + termo + "%'". Em app.py:69 o SQL do cliente é executado diretamente (tratado em F-02).
Impact: Login como admin com email "admin@loja.com' --", extração de dados via /produtos/busca?q= e alteração arbitrária de registros. Um nome com apóstrofo ("Teclado D'Ávila") já quebra o INSERT com 500.
Recommendation: Substituir todas as concatenações listadas por placeholders "?" com tupla de parâmetros; em buscar_produtos, montar cláusulas fixas com parâmetros ("nome LIKE ?", f"%{termo}%"); remover a execução de SQL do cliente (F-02) (PB-02).

### F-06 [HIGH] Global Mutable State / Tight Coupling to DB connection
Anti-pattern: AP-07 (AP-09)
File: app.py:4, 49, 66; controllers.py:3, 266; database.py:4, 8-10
Description: A conexão SQLite é um singleton de módulo (global db_connection) aberto com check_same_thread=False e compartilhado entre threads e requisições. Controllers e app.py importam get_db e executam SQL diretamente.
Impact: Requisições concorrentes compartilham cursor e transação: o commit de uma requisição confirma escritas parciais de outra. Não há como substituir o banco em testes.
Recommendation: (1) Abrir uma conexão por requisição em flask.g (get_db) e fechá-la em teardown_appcontext, sem global e sem check_same_thread=False; (2) mover a criação de schema e o seed para init_db(), chamado por create_app(); (3) controllers e app.py deixam de importar get_db, e o acesso a dados passa a ser feito só pelos models (PB-07).

### F-07 [HIGH] Insecure Runtime Configuration
Anti-pattern: AP-10
File: app.py:8, 9, 88; controllers.py:286, 288
Description: DEBUG=True e debug=True fixos, bind fixo em 0.0.0.0 e CORS(app) aberto para qualquer origem. O /health declara "ambiente": "producao" com "debug": True.
Impact: O debugger do Werkzeug fica exposto na rede, permitindo execução remota de código. Qualquer site pode chamar a API a partir do navegador da vítima.
Recommendation: (1) Ler DEBUG de FLASK_DEBUG (padrão False) em config/settings.py, removendo DEBUG=True e debug=True de app.py:8 e 88; (2) ler o host de HOST (padrão 127.0.0.1) em vez do 0.0.0.0 fixo; (3) restringir o CORS às origens de CORS_ORIGINS (padrão http://localhost:5000); (4) o campo "ambiente" do /health passa a vir da config, e "debug" é removido (PB-01).

### F-08 [HIGH] Business Logic in Controller/Route
Anti-pattern: AP-06
File: app.py:47-57, 59-78; controllers.py:52-54, 208-210, 242, 247-250, 266-274
Description: Os handlers executam SQL (reset-db, query, contagens do health_check), disparam efeitos colaterais ("ENVIANDO EMAIL/SMS/PUSH", notificações de aprovação e cancelamento) e definem as listas de domínio (categorias válidas, status válidos) inline.
Impact: As regras ficam presas à camada HTTP: não podem ser reutilizadas nem testadas, e trocar o envio de notificações exige mexer em cada handler.
Recommendation: (1) Mover as notificações de controllers.py:208-210 e 247-250 para services/notification_service.py, chamado pelo controller; (2) mover as contagens do health (controllers.py:266-274) para models/sistema_model.py; (3) mover o reset do banco (app.py:49-56) para o model, com a rota em views/sistema_routes.py; (4) transformar as listas de categorias (controllers.py:52) e status (controllers.py:242) em constantes de domínio no model, usadas pela validação (PB-06, PB-14).

### F-09 [HIGH] Missing Transaction in Multi-write Flow
Anti-pattern: AP-08
File: models.py:133-169
Description: criar_pedido faz INSERT em pedidos, INSERT em itens_pedido por item e UPDATE de estoque sem transação explícita nem rollback. O estoque é verificado (140-145) e baixado depois (163-166) sem atomicidade, e o preço é relido (155).
Impact: Uma falha no meio deixa o pedido sem itens ou com estoque parcialmente baixado. Pedidos concorrentes podem vender mais do que o estoque (estoque negativo).
Recommendation: Executar criar_pedido numa única transação (with conn / BEGIN IMMEDIATE) com rollback em qualquer erro; baixar o estoque com "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?", verificando o rowcount; reutilizar o preço lido na validação em vez de relê-lo (PB-08).

### F-10 [MEDIUM] Scattered or Swallowed Error Handling
Anti-pattern: AP-14
File: app.py:77-78; controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292
Description: Todos os handlers repetem try/except Exception e devolvem str(e) ao cliente. Não há handler central.
Impact: Detalhes internos (mensagens do SQLite, nomes de colunas) vazam e ajudam a explorar F-05. Há 17 cópias do mesmo tratamento.
Recommendation: Criar middlewares/error_handler.py com @app.errorhandler(Exception) devolvendo 500 {"erro": "Erro interno do servidor"} e log da exceção; remover os try/except repetidos (PB-12).

### F-11 [MEDIUM] Duplicated Logic
Anti-pattern: AP-12
File: controllers.py:28-46, 72-90; models.py:12-21, 31-40, 79-86, 95-102, 171-201, 203-233, 304-313
Description: A conversão row→dict de produto aparece 3 vezes e a de usuário 2 vezes. A montagem de pedidos com itens está duplicada inteira (get_pedidos_usuario e get_todos_pedidos), e a validação de produto está copiada entre criar e atualizar.
Impact: As correções precisam ser replicadas em vários pontos. O update já divergiu do create (sem limites de nome nem validação de categoria).
Recommendation: Helpers únicos _produto_to_dict/_usuario_to_dict, uma função única para carregar pedidos com itens (com filtro opcional por usuário) e um validador de produto compartilhado por create e update (PB-10).

### F-12 [MEDIUM] Missing Input Validation
Anti-pattern: AP-13
File: controllers.py:43-50, 81-90, 118-121, 153-158, 169-171, 195-201, 239-240; models.py:139-146
Description: preco/estoque não têm o tipo checado ("abc" < 0 → TypeError); update sem limites de nome nem validação de categoria; preco_min inválido quebra float(); login e atualização de status sem body → AttributeError; itens sem produto_id/quantidade → KeyError; quantidade ≤ 0 é aceita; email sem validação de formato.
Impact: Entradas inválidas resultam em 500 em vez de 400. Uma quantidade negativa cria pedido com total negativo e aumenta o estoque.
Recommendation: Validação na borda (controllers/validation.py): body JSON obrigatório, preco numérico ≥ 0, estoque inteiro ≥ 0, mesmas regras no create e no update, filtros numéricos com 400, itens com produto_id e quantidade inteiros > 0, email com formato válido (PB-11).

### F-13 [MEDIUM] Broken Referential Integrity on Delete
Anti-pattern: AP-16
File: database.py:45-53; models.py:65-70, 196, 228, 279-283
Description: DELETE /produtos/<id> remove fisicamente o produto ainda referenciado por itens_pedido (sem FK), e os pedidos passam a exibir "Desconhecido" (196, 228 admitem a inconsistência). atualizar_status_pedido responde sucesso sem checar o rowcount.
Impact: O histórico de pedidos perde o nome dos produtos. PUT /pedidos/999/status responde 200 "Status atualizado" para um pedido inexistente.
Recommendation: Soft delete (ativo = 0) com listagem e busca filtrando ativo = 1, preservando o histórico; criar_pedido rejeita produto inativo; atualizar_status_pedido retorna 404 quando o rowcount for 0 (PB-16).

### F-14 [MEDIUM] N+1 Queries
Anti-pattern: AP-11
File: models.py:187-199, 219-231
Description: Para cada pedido é feita 1 query de itens, e para cada item 1 query de nome do produto (cursor2/cursor3 dentro de loops).
Impact: GET /pedidos com P pedidos e I itens faz 1 + P + I queries, e a latência cresce linearmente com o histórico.
Recommendation: Carregar itens e nomes com uma única query JOIN itens_pedido × produtos (LEFT JOIN) agrupada em Python (PB-09).

### F-15 [LOW] Print as Logging
Anti-pattern: AP-20
File: app.py:56, 83-86; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Description: Os eventos e erros são registrados com print, inclusive os emails em login com sucesso e com falha.
Impact: Sem níveis nem destino configurável: o log fica ruidoso e não dá para filtrá-lo em produção.
Recommendation: Usar logging.getLogger(__name__) com níveis (info/warning/exception) (PB-15).

### F-16 [LOW] Magic Numbers / Strings
Anti-pattern: AP-18
File: app.py:88; controllers.py:47-50, 52, 242; models.py:257-262
Description: As faixas de desconto (10000/0.1, 5000/0.05, 1000/0.02), os limites de nome (2, 200), as listas literais de categorias e status e a porta 5000 aparecem como literais.
Impact: As regras de negócio ficam implícitas e são difíceis de ajustar com segurança.
Recommendation: Constantes nomeadas no model/config (DESCONTO_FAIXAS, NOME_MIN/MAX, CATEGORIAS_VALIDAS, STATUS_VALIDOS, PORT) (PB-15).

### F-17 [LOW] Non-idiomatic Constructs
Anti-pattern: AP-22
File: controllers.py:8, 54, 57, 106, 161, 200; models.py:63, 70, 143, 145, 283
Description: Concatenação de strings em vez de f-string, "if not itens or len(itens) == 0" redundante e "return True" sem significado.
Impact: Mais ruído e menos legibilidade.
Recommendation: Usar f-strings, simplificar para "if not itens" e retornar valores úteis (rowcount) (PB-15).

### F-18 [LOW] Poor Naming
Anti-pattern: AP-19
File: controllers.py:14, 56, 64, 98, 136, 160; models.py:24, 54, 65, 89, 187, 191, 219, 223
Description: "id" sombreia o builtin, e há cursores com sufixo numérico (cursor2, cursor3).
Impact: Confusão de leitura e risco de bugs sutis ao usar id().
Recommendation: Renomear para produto_id/usuario_id e eliminar cursor2/cursor3 com a query única de F-14 (PB-15).

### F-19 [LOW] Dead Code / Unused Imports
Anti-pattern: AP-21
File: database.py:2; models.py:2
Description: "import os" (database.py) e "import sqlite3" (models.py) não são usados.
Impact: Ruído e dependências aparentes falsas.
Recommendation: Remover os imports não usados (PB-15).

### F-20 [LOW] Redundant Queries
Anti-pattern: AP-17
File: models.py:239-254
Description: O relatório de vendas faz 5 queries separadas na tabela pedidos (COUNT, SUM e 3× COUNT por status).
Impact: Round-trips desnecessários e números de queries distintas podem ficar inconsistentes entre si.
Recommendation: Uma única query com COUNT(*), SUM(total) e SUM(CASE WHEN status = ... THEN 1 ELSE 0 END) (PB-09).

================================
Total: 20 findings
================================
