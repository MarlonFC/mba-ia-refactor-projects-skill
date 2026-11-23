module.exports = ({ userModel }) => ({
  deleteUser: (userId) => userModel.delete(userId),
});
