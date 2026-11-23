module.exports = ({ courseModel }) => ({
  financialReport: () => courseModel.financialReport(),
});
