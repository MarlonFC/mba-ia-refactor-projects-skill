const express = require('express');
const { asyncHandler } = require('../middlewares/errorHandler');

// Texto mantido por compatibilidade com o contrato original; os dependentes agora são removidos.
const USER_DELETED_MESSAGE = 'Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.';

module.exports = (userController) => {
  const router = express.Router();

  router.delete('/api/users/:id', asyncHandler(async (req, res) => {
    await userController.deleteUser(req.params.id);
    res.send(USER_DELETED_MESSAGE);
  }));

  return router;
};
