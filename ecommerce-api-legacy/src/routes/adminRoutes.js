const express = require('express');
const { asyncHandler } = require('../middlewares/errorHandler');

module.exports = (reportController, requireAdmin) => {
  const router = express.Router();
  router.get('/api/admin/financial-report', requireAdmin, asyncHandler(reportController.financialReport));
  return router;
};
