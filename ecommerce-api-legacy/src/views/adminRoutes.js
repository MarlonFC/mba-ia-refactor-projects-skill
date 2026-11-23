const express = require('express');
const requireAdmin = require('../middlewares/auth');
const { asyncHandler } = require('../middlewares/errorHandler');

module.exports = (reportController) => {
  const router = express.Router();

  router.get('/api/admin/financial-report', requireAdmin, asyncHandler(async (req, res) => {
    res.json(await reportController.financialReport());
  }));

  return router;
};
