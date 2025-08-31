"""Game routes: create/join game, get state, submit guesses.

MVP: in-memory only. Not production safe (no auth, no persistence).
"""

from __future__ import annotations

import uuid
from flask import Blueprint, request, jsonify
from util.route_builder import RouteBuilder
from util.lobby import Lobby
from util.game import get_or_create_game, GAMES

bp = Blueprint('game', __name__)

LOBBIES: dict[str, Lobby] = {}


def _get_lobby(lobby_id: str) -> Lobby | None:
    return LOBBIES.get(lobby_id)


def create_game():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    duration = int(data.get('durationSeconds') or 900)
    if not username:
        return jsonify({'error': 'username_required'}), 400
    lobby_id = uuid.uuid4().hex[:8]
    lobby = Lobby(lobby_id)
    lobby.add_player(username)
    LOBBIES[lobby_id] = lobby
    game = get_or_create_game(lobby_id, duration)
    return jsonify({'lobbyId': lobby_id, 'player': username, 'state': game.summary()}), 201


def join_game(lobby_id: str):
    data = request.json or {}
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({'error': 'username_required'}), 400
    lobby = _get_lobby(lobby_id)
    if not lobby:
        return jsonify({'error': 'lobby_not_found'}), 404
    lobby.add_player(username)
    game = get_or_create_game(lobby_id)
    return jsonify({'lobbyId': lobby_id, 'player': username, 'state': game.summary()}), 200


def game_state(lobby_id: str):
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'not_found'}), 404
    lobby = LOBBIES.get(lobby_id)
    return jsonify({"lobby": lobby.to_dict() if lobby else None, "game": game.detailed_state()})


def submit_guess(lobby_id: str):
    data = request.json or {}
    guess = data.get('guess') or ''
    player = data.get('player') or ''
    if not guess:
        return jsonify({'error': 'guess_required'}), 400
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'game_not_found'}), 404
    result = game.submit_guess(player, guess)
    return jsonify(result), (200 if result.get('accepted') else 400)


def lobby_players(lobby_id: str):
    lobby = _get_lobby(lobby_id)
    if not lobby:
        return jsonify({'error': 'lobby_not_found'}), 404
    return jsonify(lobby.to_dict())


def reset_game(lobby_id: str):
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'game_not_found'}), 404
    game.reset()
    return jsonify({'status': 'reset', 'state': game.summary()})


def start_game(lobby_id: str):
    game = GAMES.get(lobby_id)
    if not game:
        # Auto-create if lobby exists
        if lobby_id in LOBBIES:
            game = get_or_create_game(lobby_id)
        else:
            return jsonify({'error': 'lobby_not_found'}), 404
    status = game.start()
    return jsonify({'status': status, 'state': game.summary()})


RouteBuilder(bp) \
    .route('/games') \
    .methods('POST') \
    .handler(create_game) \
    .build()

RouteBuilder(bp) \
    .route('/games/<lobby_id>/join') \
    .methods('POST') \
    .handler(join_game) \
    .build()

RouteBuilder(bp) \
    .route('/games/<lobby_id>/state') \
    .methods('GET') \
    .handler(game_state) \
    .build()

RouteBuilder(bp) \
    .route('/games/<lobby_id>/guess') \
    .methods('POST') \
    .handler(submit_guess) \
    .build()

RouteBuilder(bp) \
    .route('/games/<lobby_id>/players') \
    .methods('GET') \
    .handler(lobby_players) \
    .build()

RouteBuilder(bp) \
    .route('/games/<lobby_id>/reset') \
    .methods('POST') \
    .handler(reset_game) \
    .build()

RouteBuilder(bp) \
    .route('/games/<lobby_id>/start') \
    .methods('POST') \
    .handler(start_game) \
    .build()
