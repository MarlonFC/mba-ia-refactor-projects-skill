// Configuração lida do ambiente. Nenhum segredo literal no código.
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  // Sem valor padrão: rotas admin ficam fechadas (401) até ADMIN_TOKEN ser definido.
  adminToken: process.env.ADMIN_TOKEN || '',
});
