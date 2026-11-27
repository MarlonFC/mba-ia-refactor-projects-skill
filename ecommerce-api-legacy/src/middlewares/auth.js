const crypto = require('crypto');

// Exige X-Admin-Token igual ao token configurado; sem token configurado, tudo é negado.
const createRequireAdmin = (adminToken) => (req, res, next) => {
  const expected = Buffer.from(adminToken);
  const provided = Buffer.from(req.get('X-Admin-Token') || '');
  if (!expected.length || provided.length !== expected.length || !crypto.timingSafeEqual(provided, expected)) {
    return res.status(401).send('Não autorizado');
  }
  return next();
};

module.exports = { createRequireAdmin };
