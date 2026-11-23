================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.13 + Flask 3.1.1 (SQLite)
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 5 | HIGH: 6 | MEDIUM: 5 | LOW: 6
Deprecated APIs: none detected for Python 3.13 + Flask 3.1.1

## Findings

### F-01 [CRITICAL] Hardcoded Credentials / Secrets
Anti-pattern: AP-01
File: app.py:7; controllers.py:286-289
Description: SECRET_KEY é o literal "minha-chave-super-secreta-123" em app.py:7. O GET /health devolve esse mesmo segredo no campo "secret_key", junto com "db_path", "debug" e "ambiente".
Impact: Qualquer pessoa que leia o repositório ou chame /health obtém a chave de assinatura da aplicação e consegue forjar sessões ou tokens assinados com ela.
Recommendation: Ler SECRET_KEY de variável de ambiente num módulo de config e retirar segredos e detalhes internos da resposta do health check (PB-01).

### F-02 [CRITICAL] Unprotected Dangerous Endpoint (admin)
Anti-pattern: AP-04
File: app.py:47-57, 59-78
Description: POST /admin/reset-db apaga todas as tabelas, e POST /admin/query executa qualquer SQL vindo de dados["sql"] (cursor.execute(query) em app.py:69). Nenhuma das duas rotas tem autenticação ou autorização.
Impact: Um cliente anônimo pode apagar o banco inteiro, ler a tabela usuarios (com senhas) ou alterar qualquer dado. É execução remota de SQL.
Recommendation: Remover o endpoint de SQL arbitrário e retirar o reset-db da API pública, ou deixá-lo atrás de uma flag de config desligada por padrão (PB-04).

### F-03 [CRITICAL] God Module
Anti-pattern: AP-05
File: controllers.py:1-292; models.py:1-314
Description: models.py (314 linhas) junta acesso a dados de produtos, usuários e pedidos com regras de negócio: checagem de estoque e cálculo do total (models.py:139-146) e faixas de desconto (models.py:256-262). controllers.py (292 linhas) trata HTTP dos três domínios, guarda regras (categorias válidas, status, notificações) e ainda executa SQL direto (controllers.py:266-274).
Impact: Qualquer mudança mexe em arquivos que misturam camadas e domínios. Não há como testar regras de negócio sem banco e sem HTTP, e o risco de regressão cresce.
Recommendation: Separar por domínio e por camada: repositórios/models com SQL, services com regras, controllers e blueprints com HTTP (PB-05).

### F-04 [CRITICAL] Insecure Password Storage / Sensitive Data Exposure
Anti-pattern: AP-03
File: database.py:31, 76-78; models.py:83, 99, 109-111, 126-129
Description: As senhas são gravadas em texto plano tanto no seed quanto em criar_usuario. O login compara a senha direto na query (WHERE senha = '...'). get_todos_usuarios e get_usuario_por_id serializam o campo "senha", que sai em GET /usuarios e GET /usuarios/<id>.
Impact: Um vazamento do banco expõe todas as senhas. Hoje basta chamar GET /usuarios para listar a senha de todos os usuários, inclusive a do admin.
Recommendation: Guardar hash com salt (werkzeug.security.generate_password_hash, que já vem com o Flask), comparar com check_password_hash e nunca serializar a senha (PB-03).

### F-05 [CRITICAL] SQL Injection
Anti-pattern: AP-02
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-299
Description: Todas as queries com valores de entrada são montadas por concatenação, por exemplo "SELECT * FROM usuarios WHERE email = '" + email + "'" e "nome LIKE '%" + termo + "%'". A execução de SQL arbitrário em app.py:69 já está coberta no F-02.
Impact: Dá para logar sem senha usando o email "admin@loja.com' --". A busca (?q=) e o cadastro de produto/usuário permitem ler e alterar qualquer tabela. Um apóstrofo legítimo, como em "Monitor 27''", gera erro 500.
Recommendation: Usar parâmetros do driver ("... WHERE id = ?", (id,)) em todas as queries, inclusive na busca dinâmica (PB-02).

### F-06 [HIGH] Tight Coupling / No Dependency Injection
Anti-pattern: AP-09
File: app.py:4; controllers.py:3; models.py:1
Description: Rotas, controllers e models importam o get_db concreto do módulo global database. Controllers chamam models e get_db() ao mesmo tempo (controllers.py:2-3).
Impact: Não dá para trocar o banco nem injetar um banco de teste. Cada camada depende diretamente da infraestrutura.
Recommendation: Fornecer a conexão por requisição via flask.g/app context num módulo db, de forma que só a camada de dados acesse a conexão (PB-07).

### F-07 [HIGH] Insecure Runtime Configuration
Anti-pattern: AP-10
File: app.py:8, 9, 88; controllers.py:286, 288
Description: DEBUG=True está fixo, assim como app.run(host="0.0.0.0", debug=True) e CORS(app) aberto para qualquer origem. O /health se declara "ambiente": "producao" e ao mesmo tempo "debug": True.
Impact: O debugger do Werkzeug fica exposto na rede (execução de código pelo console de erro), e qualquer site pode chamar a API pelo navegador.
Recommendation: Tirar debug, host e origens CORS de variáveis de ambiente, com defaults seguros, num módulo de config (PB-01).

### F-08 [HIGH] Unprotected Dangerous Endpoint (mutações sem auth)
Anti-pattern: AP-04
File: app.py:15-16, 26
Description: PUT/DELETE /produtos/<id> e PUT /pedidos/<id>/status alteram ou removem dados sem nenhuma autenticação. A API não tem sistema de auth (escalonamento HIGH do catálogo).
Impact: Qualquer cliente pode apagar produtos, alterar preços ou aprovar e cancelar pedidos de terceiros.
Recommendation: Criar um mecanismo de autenticação/autorização para operações administrativas. Isso muda o contrato e deve ser feito em tarefa própria (PB-04).

### F-09 [HIGH] Business Logic in Controller/Route (Fat Controller)
Anti-pattern: AP-06
File: app.py:49-55, 66-76; controllers.py:52-54, 208-210, 242, 247-250, 266-274
Description: Rotas e controllers fazem coisas que não são HTTP:
- executam SQL diretamente (reset-db, admin/query, health_check);
- guardam as listas de categorias e de status válidos;
- disparam efeitos colaterais de notificação (e-mail, SMS, push, aprovação, cancelamento) dentro do handler.
Impact: Regras duplicadas e impossíveis de reutilizar ou testar sem HTTP. A "devolução de estoque" no cancelamento é só anunciada num print e nunca acontece.
Recommendation: Levar regras, constantes de domínio e notificações para uma camada de services. Controllers só validam a entrada e delegam (PB-06, PB-14).

### F-10 [HIGH] Global Mutable State
Anti-pattern: AP-07
File: database.py:4, 8-10
Description: db_connection é um singleton global reatribuído com "global" e aberto com check_same_thread=False. Uma única conexão SQLite é compartilhada por todas as requisições e threads.
Impact: Requisições concorrentes dividem cursores e transações. Uma escrita não confirmada de uma requisição que falhou acaba commitada pela próxima, e há risco de "database is locked" e de estado inconsistente.
Recommendation: Abrir uma conexão por requisição (flask.g) e fechá-la em teardown_appcontext (PB-07).

### F-11 [HIGH] Missing Transaction in Multi-write Flow
Anti-pattern: AP-08
File: models.py:139-169
Description: criar_pedido checa o estoque e depois insere pedido, itens e baixa de estoque em passos separados, sem transação explícita nem rollback. Uma exceção no meio, como KeyError em item["quantidade"], deixa escritas pendentes na conexão compartilhada.
Impact: Podem surgir pedidos sem itens ou estoque baixado sem pedido, e essas escritas são commitadas pela próxima requisição. Duas compras simultâneas podem vender além do estoque.
Recommendation: Fazer o fluxo inteiro numa única transação ("with conn:" com rollback em erro) e baixar o estoque condicionalmente (PB-08).

### F-12 [MEDIUM] Scattered or Swallowed Error Handling
Anti-pattern: AP-14
File: app.py:77-78; controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292
Description: Cada handler repete "try/except Exception as e" e devolve str(e) ao cliente com status 500. Não existe errorhandler central.
Impact: Mensagens internas (SQL, stack, nomes de colunas) vazam ao cliente, ajudando quem explora o F-05. Além disso, a mesma lógica aparece 17 vezes.
Recommendation: Criar um error handler central (app.errorhandler) que registra a exceção e devolve uma mensagem genérica, e remover os try/except dos handlers (PB-12).

### F-13 [MEDIUM] Duplicated Logic
Anti-pattern: AP-12
File: controllers.py:28-35, 43-46, 72-79, 87-90, 242; models.py:12-21, 31-40, 79-86, 95-102, 171-201, 203-233, 247-253, 304-313
Description: Há quatro duplicações:
- A conversão row→dict de produto aparece 3 vezes e a de usuário 2 vezes.
- get_pedidos_usuario e get_todos_pedidos são quase idênticas.
- A validação de produto está copiada entre criar e atualizar.
- Os status de pedido estão listados tanto no controller quanto no relatório.
Impact: Uma alteração de campo ou regra precisa ser repetida em vários pontos, e as cópias já divergiram (ver F-14).
Recommendation: Centralizar serialização, validação de produto, consulta de pedidos e constantes de status em funções únicas (PB-10).

### F-14 [MEDIUM] Missing Input Validation
Anti-pattern: AP-13
File: controllers.py:43-50, 81-90, 153-158, 169-170, 196-201, 239-245
Description: Faltam várias validações:
- Login e status não tratam body nulo: dados.get num None gera 500.
- preco/estoque não têm o tipo checado: uma string dá TypeError e 500.
- O update não valida tamanho do nome nem categoria, ao contrário do create.
- O email não tem validação de formato.
- Os itens do pedido não têm produto_id/quantidade validados: campo ausente dá 500, e quantidade negativa aumenta o estoque.
- O update de status responde 200 mesmo para pedido inexistente.
Impact: Entradas inválidas viram erros 500 ou dados corrompidos (estoque inflado, produto com categoria inválida).
Recommendation: Validar presença, tipo e faixa na borda com retorno 400, e usar as mesmas regras em create e update (PB-11).

### F-15 [MEDIUM] Broken Referential Integrity on Delete
Anti-pattern: AP-16
File: database.py:46-52; models.py:65-70
Description: itens_pedido.produto_id e pedidos.usuario_id não têm FOREIGN KEY. deletar_produto remove o produto sem considerar os itens_pedido que o referenciam.
Impact: Pedidos antigos passam a mostrar "Desconhecido" no lugar do nome do produto, e o histórico de vendas fica inconsistente.
Recommendation: Bloquear com 409 a exclusão de produto referenciado em pedidos, ou fazer soft delete via a coluna "ativo" que já existe (PB-16).

### F-16 [MEDIUM] N+1 Queries
Anti-pattern: AP-11
File: models.py:186-199, 219-231
Description: Para cada pedido há uma query de itens, e para cada item outra query do nome do produto (cursor2/cursor3 dentro de loops).
Impact: Listar N pedidos com M itens faz 1 + N + N·M queries, e a latência cresce linearmente com o volume.
Recommendation: Buscar itens e nomes com um único JOIN itens_pedido × produtos e agrupar em memória (PB-09).

### F-17 [LOW] Print as Logging
Anti-pattern: AP-20
File: app.py:56, 83-86; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Description: Eventos da aplicação e erros vão para stdout via print(), inclusive o email de quem tentou logar.
Impact: Não há níveis, nem como filtrar ou desligar, nem integração com observabilidade, e há dados pessoais nos logs.
Recommendation: Usar logging.getLogger(__name__) com níveis adequados e sem dados pessoais (PB-15).

### F-18 [LOW] Magic Numbers / Strings
Anti-pattern: AP-18
File: app.py:36, 88; controllers.py:47-50, 52, 242, 285; models.py:257-262
Description: Vários valores de negócio são literais soltos: faixas de desconto (10000/0.1, 5000/0.05, 1000/0.02), limites de nome (2/200), lista de categorias, lista de status, porta 5000 e versão "1.0.0" repetida.
Impact: Regras de negócio ficam escondidas e são fáceis de alterar de forma inconsistente.
Recommendation: Transformar esses valores em constantes nomeadas no domínio e na config (PB-15).

### F-19 [LOW] Non-idiomatic Constructs
Anti-pattern: AP-22
File: controllers.py:8, 54, 57, 106, 200; models.py:12-21, 146
Description: Há string montada por concatenação + str() em vez de f-string, a checagem redundante "if not itens or len(itens) == 0", "total = total + ..." e dicts montados campo a campo em vez de dict(row).
Impact: Código mais verboso e mais propenso a erro.
Recommendation: Usar f-strings, truthiness, "+=" e dict(row)/serializadores (PB-15).

### F-20 [LOW] Poor Naming
Anti-pattern: AP-19
File: controllers.py:14, 56, 64, 98, 136, 160; models.py:24, 54, 65, 89, 187, 191, 219, 223
Description: O parâmetro/variável "id" sombreia o builtin, e há cursores numerados cursor2/cursor3.
Impact: Leitura mais difícil e risco de bug ao usar id() mais adiante.
Recommendation: Renomear para produto_id/usuario_id e eliminar os cursores numerados (PB-15).

### F-21 [LOW] Redundant Queries
Anti-pattern: AP-17
File: controllers.py:268-274; models.py:239-254
Description: O relatório faz 5 queries separadas (COUNT, SUM e 3 COUNTs por status), e o health check faz um "SELECT 1" seguido de 3 COUNTs.
Impact: Mais idas ao banco do que o necessário.
Recommendation: Fazer uma agregação única com SUM(CASE WHEN status = ...) (PB-09).

### F-22 [LOW] Dead Code / Unused Imports
Anti-pattern: AP-21
File: database.py:2; models.py:2, 63, 70, 283
Description: "import os" e "import sqlite3" não são usados, e os "return True" de atualizar/deletar produto e atualizar_status_pedido nunca são consumidos.
Impact: Ruído e uma falsa impressão de que existe sinalização de sucesso ou falha.
Recommendation: Remover os imports e fazer os retornos refletirem rowcount, que é usado no F-14/F-15 (PB-15).

================================
Total: 22 findings
================================
