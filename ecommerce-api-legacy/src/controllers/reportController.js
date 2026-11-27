const createReportController = (reportService) => ({
  async financialReport(req, res) {
    res.json(await reportService.financialReport());
  },
});

module.exports = { createReportController };
