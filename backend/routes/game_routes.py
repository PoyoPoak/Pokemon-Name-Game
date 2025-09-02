"""Application game routes.

# TODO Add documentation for what this file does and it's routes/capabilities

"""
import uuid
from flask import Blueprint, request, jsonify
from util.route_builder import RouteBuilder
from util.lobby import Lobby
from util.game import get_or_create_game, GAMES

bp = Blueprint('game', __name__)

# In memory lobby storage as {lobby_code: Lobby object}
ACTIVE_LOBBIES: dict[str, Lobby] = {}


# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------


def _get_lobby(lobby_id: str) -> Lobby | None:
    """Get a lobby by its ID.

    Args:
        lobby_id (str): The ID of the lobby.

    Returns:
        Lobby: The lobby object if found, otherwise None.
    """
    return ACTIVE_LOBBIES.get(lobby_id)


def create_game():
    """Create a new game lobby.

    Returns:
        Response: The response object containing the lobby ID and player information.
    """
    data = request.json or {}
    username = (data.get('username') or '').strip()
    lobby_id = uuid.uuid4().hex[:8]
    lobby = Lobby(lobby_id)
    lobby.add_player(username)
    ACTIVE_LOBBIES[lobby_id] = lobby
    game = get_or_create_game(lobby_id)
    return jsonify({'lobbyId': lobby_id, 'player': username, 'state': game.summary()}), 201


def join_game(lobby_id: str):
    """Join an existing game lobby.

    Args:
        lobby_id (str): The ID of the lobby to join.

    Returns:
        Response: The response object containing the lobby ID and player information.
    """
    data = request.json or {}
    username = (data.get('username') or '').strip()
    lobby = _get_lobby(lobby_id)
    if not lobby:
        return jsonify({'error': 'lobby_not_found'}), 404
    lobby.add_player(username)
    game = get_or_create_game(lobby_id) 
    return jsonify({'lobbyId': lobby_id, 'player': username, 'state': game.summary()}), 200


def game_state(lobby_id: str):
    """Get the current state of the game lobby.

    Args:
        lobby_id (str): The ID of the lobby.

    Returns:
        Response: The response object containing the lobby and game state information.
    """
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'not_found'}), 404
    lobby = ACTIVE_LOBBIES.get(lobby_id)
    return jsonify({"lobby": lobby.to_dict() if lobby else None, "game": game.detailed_state()}), 200


def submit_guess(lobby_id: str):
    """Submit a guess for the current game.

    Args:
        lobby_id (str): The ID of the lobby.

    Returns:
        Response: The response object containing the result of the guess submission.
    """
    data = request.json or {}
    guess = data.get('guess') or ''
    player = data.get('player') or ''
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'game_not_found'}), 404
    result = game.submit_guess(player, guess)
    if result.get('accepted'):
        lobby = _get_lobby(lobby_id)
        if lobby and player:
            lobby.add_score(player, 1)
            result['players'] = lobby.to_dict().get('players', [])
            try:
                print(f"[DEBUG] Score update: lobby={lobby_id} player={player} score={lobby.get_player(player).score}")
            except Exception:
                pass
    return jsonify(result), (200 if result.get('accepted') else 400)


def lobby_players(lobby_id: str):
    """Get the list of players in the lobby.

    Args:
        lobby_id (str): The ID of the lobby.

    Returns:
        Response: The response object containing the list of players in the lobby.
    """
    lobby = _get_lobby(lobby_id)
    if not lobby:
        return jsonify({'error': 'lobby_not_found'}), 404
    return jsonify(lobby.to_dict())


def reset_game(lobby_id: str):
    """Reset the game in the specified lobby.

    Args:
        lobby_id (str): The ID of the lobby.

    Returns:
        Response: The response object containing the status of the reset operation.
    """
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'game_not_found'}), 404
    game.reset()
    return jsonify({'status': 'reset', 'state': game.summary()})


def start_game(lobby_id: str):
    """Start the game in the specified lobby.

    Args:
        lobby_id (str): The ID of the lobby.

    Returns:
        Response: The response object containing the status of the start operation.
    """
    game = GAMES.get(lobby_id)
    if not game:
        # Auto-create if lobby exists
        if lobby_id in ACTIVE_LOBBIES:
            game = get_or_create_game(lobby_id)
        else:
            return jsonify({'error': 'lobby_not_found'}), 404
    status = game.start()
    return jsonify({'status': status, 'state': game.summary()})

def pause_game(lobby_id: str):
    """Pause the game in the specified lobby.

    Args:
        lobby_id (str): The ID of the lobby.

    Returns:
        Response: The response object containing the status of the pause operation.
    """
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'game_not_found'}), 404
    status = game.pause()
    return jsonify({'status': status, 'state': game.summary()})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


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

RouteBuilder(bp) \
    .route('/games/<lobby_id>/pause') \
    .methods('POST') \
    .handler(pause_game) \
    .build()

