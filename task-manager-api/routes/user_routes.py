from flask import Blueprint, jsonify, request

from controllers import user_controller

user_bp = Blueprint('users', __name__)


@user_bp.get('/users')
def get_users():
    return jsonify(user_controller.list_users()), 200


@user_bp.get('/users/<int:user_id>')
def get_user(user_id):
    return jsonify(user_controller.get_user(user_id)), 200


@user_bp.post('/users')
def create_user():
    return jsonify(user_controller.create_user(request.get_json())), 201


@user_bp.put('/users/<int:user_id>')
def update_user(user_id):
    return jsonify(user_controller.update_user(user_id, request.get_json())), 200


@user_bp.delete('/users/<int:user_id>')
def delete_user(user_id):
    user_controller.delete_user(user_id)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


@user_bp.get('/users/<int:user_id>/tasks')
def get_user_tasks(user_id):
    return jsonify(user_controller.list_user_tasks(user_id)), 200


@user_bp.post('/login')
def login():
    return jsonify(user_controller.login(request.get_json())), 200
