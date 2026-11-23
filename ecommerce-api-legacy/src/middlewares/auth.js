const crypto = require('crypto');
const config = require('../config');

// Exige o header X-Admin-Token igual a ADMIN_TOKEN. Sem ADMIN_TOKEN configurado, nega sempre.
module.exports = function requireAdmin(req, res, next) {
  const provided = Buffer.from(req.get('X-Admin-Token') || '');
  const expected = Buffer.from(config.adminToken);
  const authorized = expected.length > 0
    && provided.length === expected.length
    && crypto.timingSafeEqual(provided, expected);
  if (!authorized) return res.status(401).send('Não autorizado');
  return next();
};
