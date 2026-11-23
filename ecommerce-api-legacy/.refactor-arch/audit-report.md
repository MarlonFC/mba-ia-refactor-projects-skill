================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express 4.18.2 (SQLite in-memory via sqlite3)
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 4 | HIGH: 4 | MEDIUM: 4 | LOW: 5
Deprecated APIs: none detected for Node.js 22 / Express 4

## Findings

### F-01 [CRITICAL] God Class
Anti-pattern: AP-05
File: src/AppManager.js:1-141
Description: A classe AppManager concentra criação da conexão (new sqlite3.Database), DDL e seed (initDb), regras de negócio de pagamento/matrícula, agregação do relatório financeiro e o registro das rotas HTTP (setupRoutes) de três domínios (checkout, relatório admin, usuários).
Impact: Qualquer mudança em uma regra exige mexer no arquivo que também define rotas e schema; é impossível testar regras sem subir Express e SQLite; alto risco de regressão.
Recommendation: Separar em config, database (conexão + schema/seed), models/repositories por entidade, services (checkout, relatório), controllers e routes, com composition root em app.js (PB-05).

### F-02 [CRITICAL] Insecure Password Storage / Sensitive Data Exposure
Anti-pattern: AP-03
File: src/AppManager.js:18, 45, 68; src/utils.js:17-23
Description: badCrypto() "hasheia" a senha repetindo os 2 primeiros caracteres do base64 e truncando em 10 (reversível/colidente); o seed grava a senha '123' em texto plano; senha ausente vira "123456" por padrão; o número completo do cartão e a chave do gateway são escritos no console (`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`).
Impact: Vazamento do banco expõe senhas triviais de recuperar; usuários criados sem senha compartilham a mesma credencial; logs contêm PAN de cartão e chave de produção (violação de PCI-DSS).
Recommendation: Usar crypto.scrypt com salt aleatório (biblioteca padrão), remover o log de cartão/chave (no máximo os 4 últimos dígitos) e não gravar senhas em claro no seed (PB-03).

### F-03 [CRITICAL] Unprotected Dangerous Endpoint
Anti-pattern: AP-04
File: src/AppManager.js:80, 131
Description: GET /api/admin/financial-report (receita e nomes de alunos) e DELETE /api/users/:id não têm nenhum middleware de autenticação/autorização; a API não possui sistema de auth.
Impact: Qualquer cliente anônimo lê dados financeiros e pessoais e apaga usuários arbitrários.
Recommendation: Proteger as rotas administrativas e destrutivas com middleware de autenticação/autorização (PB-04); como isso altera o contrato (401/403), avaliar se é mudança permitida.

### F-04 [CRITICAL] Hardcoded Credentials / Secrets
Anti-pattern: AP-01
File: src/utils.js:2-5
Description: Objeto config contém literais dbUser "admin_master", dbPass "senha_super_secreta_prod_123", paymentGatewayKey "pk_live_1234567890abcdef" e smtpUser no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório obtém credenciais de produção e a chave live do gateway de pagamento; rotacionar exige novo deploy.
Recommendation: Ler segredos de process.env em um módulo config centralizado, sem fallback com valor real, e remover os literais (PB-01).

### F-05 [HIGH] Tight Coupling / No Dependency Injection
Anti-pattern: AP-09
File: src/AppManager.js:7; src/app.js:8-10
Description: O construtor de AppManager instancia diretamente new sqlite3.Database(':memory:') e app.js depende da classe concreta para inicializar banco e rotas (manager.initDb(); manager.setupRoutes(app)).
Impact: Não é possível substituir o banco por um dublê em testes nem reutilizar a lógica com outra conexão.
Recommendation: Criar a conexão no composition root e injetá-la em repositories/services/controllers (PB-07).

### F-06 [HIGH] Business Logic in Controller/Route (Fat Controller)
Anti-pattern: AP-06
File: src/AppManager.js:28-78, 80-129
Description: Os handlers de rota executam SQL diretamente, decidem a aprovação do pagamento (cc.startsWith("4") ? "PAID" : "DENIED"), criam usuários, gravam auditoria e cache, e montam a agregação de receita do relatório em callbacks aninhados em até 6 níveis (callback hell).
Impact: As regras de checkout e de relatório não podem ser testadas nem reutilizadas sem HTTP; o fluxo de controle por contadores manuais é frágil e difícil de manter.
Recommendation: Mover as regras para CheckoutService/ReportService e o SQL para repositories com async/await; o controller só traduz request/response (PB-06, PB-14).

### F-07 [HIGH] Missing Transaction in Multi-write Flow
Anti-pattern: AP-08
File: src/AppManager.js:50-62, 69-71
Description: O checkout faz INSERT em users, enrollments, payments e audit_logs em chamadas independentes, sem BEGIN/COMMIT/ROLLBACK; falhas intermediárias retornam 500 após escritas já realizadas.
Impact: Falha no INSERT de pagamento deixa matrícula sem pagamento (aluno com acesso grátis) e usuários criados sem matrícula.
Recommendation: Executar o fluxo de escrita em uma transação única com rollback em erro (PB-08).

### F-08 [HIGH] Global Mutable State
Anti-pattern: AP-07
File: src/utils.js:9-10, 12-15
Description: globalCache é um objeto de módulo mutado a cada checkout por logAndCache (chave last_checkout_<id>) sem limite nem leitura; totalRevenue é um let global exportado (cópia por valor, nunca atualizado).
Impact: Crescimento de memória ilimitado proporcional ao número de usuários; estado compartilhado entre requisições e um contador de receita enganoso.
Recommendation: Remover o cache global não lido e o contador; se um cache for necessário, encapsulá-lo em uma instância injetada e limitada (PB-07).

### F-09 [MEDIUM] Missing Input Validation
Anti-pattern: AP-13
File: src/AppManager.js:29-35, 46, 132
Description: O checkout só verifica presença de usr/eml/c_id/card; não valida tipo/formato de e-mail, c_id e card. Com card numérico, cc.startsWith lança TypeError dentro do callback do sqlite. O :id do DELETE não é validado.
Impact: Um body com "card": 4111222233334444 (número) derruba o processo inteiro (exceção não capturada em callback assíncrono) → indisponibilidade; dados inválidos são persistidos.
Recommendation: Validar tipos e formatos na borda (controller/validator), retornando 400 para entrada inválida (PB-11).

### F-10 [MEDIUM] Scattered or Swallowed Error Handling
Anti-pattern: AP-14
File: src/AppManager.js:38, 57, 92-93, 104, 106, 133; src/app.js:5-10
Description: err é ignorado nos callbacks do audit_log (57), de enrollments (92-93, usa enrollments.length sem checar err), users (104), payments (106) e DELETE (133); a linha 38 trata erro de banco como 404; cada handler monta seus próprios res.status(500).send; não há middleware central de erro.
Impact: Erros de banco ficam invisíveis ou viram respostas enganosas; um erro em 92 causa TypeError e derruba o processo; a resposta pode nunca ser enviada (requisição pendurada).
Recommendation: Propagar erros via async/await para um error handler central do Express e verificar err em todos os acessos (PB-12).

### F-11 [MEDIUM] N+1 Queries
Anti-pattern: AP-11
File: src/AppManager.js:89-92, 102-106
Description: Para cada curso executa SELECT em enrollments, e para cada matrícula executa SELECT em users e outro em payments.
Impact: O relatório faz 1 + C + 2E queries; a latência cresce linearmente com o número de matrículas.
Recommendation: Uma única query com LEFT JOIN courses/enrollments/users/payments, agregada no service preservando o formato da resposta (PB-09).

### F-12 [MEDIUM] Broken Referential Integrity on Delete
Anti-pattern: AP-16
File: src/AppManager.js:131-136
Description: DELETE FROM users remove o usuário sem tratar enrollments/payments dependentes (sem FK/cascade) e responde sucesso sem checar this.changes; a própria mensagem admite "matrículas e pagamentos ficaram sujos".
Impact: Matrículas e pagamentos órfãos aparecem como 'Unknown' no relatório financeiro; deletar um id inexistente responde sucesso.
Recommendation: Remover payments → enrollments → user em transação no repository (ou FK com ON DELETE CASCADE) (PB-16).

### F-13 [LOW] Dead Code / Unused Imports
Anti-pattern: AP-21
File: src/AppManager.js:2, 104; src/utils.js:2, 3, 5, 10, 25
Description: totalRevenue é importado e nunca usado; a query seleciona email sem uso; config.dbUser, dbPass e smtpUser nunca são lidos; globalCache e totalRevenue são exportados sem consumidores.
Impact: Ruído que confunde a leitura e sugere funcionalidades inexistentes.
Recommendation: Remover imports, campos e exports não utilizados (PB-15).

### F-14 [LOW] Poor Naming
Anti-pattern: AP-19
File: src/AppManager.js:4, 29-33, 52, 89, 132; src/utils.js:17
Description: Variáveis de uma ou duas letras (u, e, p, cid, cc, c), abreviação enrId, a classe genérica AppManager e a função badCrypto (nome que descreve o defeito, não o propósito).
Impact: A intenção do código só é entendida lendo o fluxo inteiro.
Recommendation: Usar nomes de domínio (name, email, password, courseId, cardNumber, enrollmentId, hashPassword) (PB-15).

### F-15 [LOW] Non-idiomatic Constructs
Anti-pattern: AP-22
File: src/AppManager.js:26, 29-33, 43, 46, 52, 81, 90, 132
Description: const self = this junto com arrow functions; let para valores nunca reatribuídos; controle de conclusão por contadores manuais em vez de Promises/async-await.
Impact: Código propenso a erros de `this` e de sincronização; difícil de ler.
Recommendation: Usar const, async/await com wrappers Promise do sqlite3 e remover o alias self (PB-15).

### F-16 [LOW] Print/Console as Logging
Anti-pattern: AP-20
File: src/AppManager.js:45; src/app.js:13; src/utils.js:13
Description: Eventos da aplicação registrados com console.log, sem níveis nem estrutura (a linha 45 também está em F-02 por conter dados sensíveis).
Impact: Não dá para filtrar por severidade nem desligar logs de debug em produção.
Recommendation: Centralizar em um logger mínimo com níveis (console.info/console.error encapsulados) e remover logs de debug (PB-15).

### F-17 [LOW] Magic Numbers / Strings
Anti-pattern: AP-18
File: src/AppManager.js:46, 48, 68; src/utils.js:6, 18-22
Description: Regra de aprovação pelo prefixo "4", status "PAID"/"DENIED" literais, senha padrão "123456", porta 3000 fixa e as constantes 10000/2/10 do "hash".
Impact: As regras de negócio ficam escondidas em literais espalhados; mudar a porta exige editar código.
Recommendation: Extrair constantes nomeadas (PAYMENT_STATUS, APPROVED_CARD_PREFIX) e ler PORT de process.env com padrão 3000 (PB-15).

================================
Total: 17 findings
================================
