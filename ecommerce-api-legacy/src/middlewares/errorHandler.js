class AppError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Express 4 não encaminha rejeições de handlers async sem este wrapper.
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

// Respostas de erro em texto puro, como no contrato original.
// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
  if (err instanceof AppError) return res.status(err.status).send(err.message);
  if (err.expose && err.status) return res.status(err.status).send(err.message); // ex.: JSON malformado
  console.error(err);
  return res.status(500).send('Erro interno');
}

module.exports = { AppError, asyncHandler, errorHandler };
