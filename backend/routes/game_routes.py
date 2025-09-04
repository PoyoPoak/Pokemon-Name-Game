"""Game / Lobby HTTP API routes.

Overview
========
Provides all JSON endpoints for creating / joining lobbies, managing in‑memory
game instances, submitting guesses, and basic game lifecycle (start / pause /
reset) plus lightweight player listing. State is **process local & ephemeral**;
it will be lost on restart and is NOT safe for horizontal scaling.

Data Model (in-memory)
----------------------
* ACTIVE_LOBBIES: dict[lobby_id, Lobby]
* GAMES:          dict[lobby_id, Game] (imported from util.game)

Endpoints
---------
POST   /api/games                      -> create_game
POST   /api/games/<lobby_id>/join      -> join_game
GET    /api/games/<lobby_id>/state     -> game_state (summary + detailed game + lobby)
POST   /api/games/<lobby_id>/guess     -> submit_guess (adds score on success)
GET    /api/games/<lobby_id>/players   -> lobby_players
POST   /api/games/<lobby_id>/reset     -> reset_game
POST   /api/games/<lobby_id>/start     -> start_game (auto-creates game if lobby exists)
POST   /api/games/<lobby_id>/pause     -> pause_game

Response Shapes (core)
----------------------
create / join:
    { "lobbyId": str, "player": str, "state": GameSummary }

game_state:
    { "lobby": LobbySnapshot | null, "game": GameDetailed }

guess (success):
    { accepted: true, positions: [int], totalGuessed: int, remaining: int, complete: bool, event: {...}, players?: [...] }

guess (failure):
    { accepted: false, reason: str, event: {...} }

Design Notes
------------
* No authentication yet; usernames are not unique globally, only per lobby.
* Minimal validation: frontend expected to enforce non-empty username/guess.
* Timers and scoring logic live in util.game / util.lobby.
* Consider persisting & broadcasting via websockets for production scale.

Future Improvements (not implemented here)
------------------------------------------
* Auth & authorization (validate player identity)
* Persistence / Redis or database backed lobbies & games
* Rate limiting on mutating endpoints
* WebSocket or SSE push for real-time updates
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
    """Create a new lobby & associated Game instance.

    Expects JSON: { "username": str }
    Returns 201 JSON: { lobbyId, player, state }
    Frontend ensures non-empty username; backend does not reject blank.
    """
    data = request.json or {}
    username = (data.get('username') or '').strip()
    lobby_id = uuid.uuid4().hex[:8]
    lobby = Lobby(lobby_id)
    try:
        lobby.add_player(username)
    except ValueError:
        # Duplicate username in a brand new lobby is rare (same user double‑submit)
        return jsonify({'error': 'username_taken', 'message': 'That username is already taken in this lobby. Please choose another.'}), 400
    ACTIVE_LOBBIES[lobby_id] = lobby
    game = get_or_create_game(lobby_id)
    return jsonify({'lobbyId': lobby_id, 'player': username, 'state': game.summary()}), 201


def join_game(lobby_id: str):
    """Join an existing lobby.

    JSON: { "username": str }
    404 if lobby not found.
    200 JSON: { lobbyId, player, state }
    """
    data = request.json or {}
    username = (data.get('username') or '').strip()
    lobby = _get_lobby(lobby_id)
    if not lobby:
        return jsonify({'error': 'lobby_not_found', 'message': 'Lobby code not found. Double‑check and try again.'}), 404
    try:
        lobby.add_player(username)
    except ValueError:
        return jsonify({'error': 'username_taken', 'message': 'That username is already taken in this lobby. Please pick a different one.'}), 400
    game = get_or_create_game(lobby_id) 
    return jsonify({'lobbyId': lobby_id, 'player': username, 'state': game.summary()}), 200


def game_state(lobby_id: str):
    """Return combined lobby + game detailed state.

    404 if game absent. Lobby may be null if removed after game creation.
    """
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'not_found'}), 404
    lobby = ACTIVE_LOBBIES.get(lobby_id)
    return jsonify({"lobby": lobby.to_dict() if lobby else None, "game": game.detailed_state()}), 200


def submit_guess(lobby_id: str):
    """Submit a guess for the given lobby's active game.

    JSON: { guess: str, player: str }
    404 if game missing.
    On success increments player's lobby score & returns enriched result.
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
    """Return current lobby player list and aggregate score info."""
    lobby = _get_lobby(lobby_id)
    if not lobby:
        return jsonify({'error': 'lobby_not_found'}), 404
    return jsonify(lobby.to_dict())


def reset_game(lobby_id: str):
    """Hard reset game state (timer & guesses) for lobby.

    404 if game not found.
    """
    game = GAMES.get(lobby_id)
    if not game:
        return jsonify({'error': 'game_not_found'}), 404
    game.reset()
    return jsonify({'status': 'reset', 'state': game.summary()})


def start_game(lobby_id: str):
    """Start or restart (if finished) the game.

    Auto-creates a game if lobby exists but no game yet.
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
    """Pause running game (idempotent). 404 if game missing."""
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

