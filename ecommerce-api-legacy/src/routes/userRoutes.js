const express = require('express');
const { asyncHandler } = require('../middlewares/errorHandler');

module.exports = (userController, requireAdmin) => {
  const router = express.Router();
  router.delete('/api/users/:id', requireAdmin, asyncHandler(userController.deleteUser));
  return router;
};
