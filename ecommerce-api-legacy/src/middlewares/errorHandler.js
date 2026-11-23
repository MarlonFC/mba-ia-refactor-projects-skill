const { STATUS_CODES } = require('http');

class AppError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Express 4 não encaminha rejeições de handlers async para o error handler.
const asyncHandler = (handler) => (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);

// Respostas de erro em texto puro, como na API original.
function errorHandler(err, req, res, next) {
  if (err instanceof AppError) return res.status(err.status).send(err.message);
  // Erros de cliente do Express (ex.: JSON malformado → 400): mesmo status, sem expor stack trace.
  if (err.status >= 400 && err.status < 500) return res.status(err.status).send(STATUS_CODES[err.status]);
  console.error(err);
  return res.status(500).send('Erro interno');
}

module.exports = { AppError, asyncHandler, errorHandler };
