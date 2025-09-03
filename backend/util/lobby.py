"""Lobby container: manages player membership & lightweight scoring for a single game session.

High-level responsibilities:
		* Maintain a set of uniquely named `User` objects for a lobby (add / remove / lookup / list).
		* Enforce username uniqueness within the lobby boundary (case‑sensitive at present).
		* Provide a minimal scoring helper (increment per player) without game‑logic coupling.
		* Expose a stable, JSON‑serializable shape (`to_dict`) for API responses.

Design notes:
		* Purely in‑memory & process‑local: state is lost on restart and not shared across workers.
		* No locking/thread safety: acceptable for single‑process dev usage; would need synchronization
			(or external store) before introducing concurrency or multiple Gunicorn workers.
		* Only tracks aggregate lobby composition & per‑player scores; game timing / guess logic lives
			in the `Game` class (see `game.py`).

Future enhancements (out of scope for this minimal version):
		* Persistence / replication (Redis or database) to survive restarts & scale horizontally.
		* Username normalization / case‑insensitive collision policy.
		* Idle player eviction & activity timestamps.
		* Role / permission flags (host, moderator, spectator).
		* Aggregate / derived metrics (e.g., fastest guess streaks) beyond simple score incrementing.
"""
from typing import Dict, Iterable, Optional
from util.user import User


class Lobby:
	"""In‑memory lobby model.

	Core operations:
		* add_player(name) – create & register a new `User`; raises if name already present.
		* remove_player(name) – detach a player (idempotent; returns bool success).
		* get_player(name) – retrieve a `User` or None.
		* list_players() – iterable of all `User` objects (in insertion order of underlying dict).
		* add_score(name, delta) – increment an existing player's score; raises if absent.

	Serialization contract (``to_dict``):
		{
		  "id": <lobby_id>,
		  "players": [ {"name": str, "score": int}, ... ],
		  "playerCount": int,
		  "scoreTotal": int  # sum of all player scores
		}

	Constraints / assumptions:
		* Not thread‑safe; rely on single interpreter execution context.
		* Username uniqueness is exact (case & whitespace sensitive) to keep logic simple.
		* Score logic intentionally trivial—domain rules belong elsewhere.

	Error model:
		* Duplicate add -> ValueError.
		* add_score for missing player -> ValueError.

	"""
	def __init__(self, id: str):
		self.id = id	
		self.score = 0
		self.players: Dict[str, User] = {} 

	def add_player(self, user: str) -> User:
		"""Add a new player to the lobby.

		Args:
			user (str): The username of the player.

		Raises:
			ValueError: If the username is already taken.

		Returns:
			User: The User object representing the added player.
		"""
		if user in self.players:
			raise ValueError(f"Username '{user}' already exists; choose a different name.")
		u = User(user)
		self.players[user] = u
		return u

	def remove_player(self, user: str) -> bool:
		"""Remove a player from the lobby.

		Args:
			user (str): The username of the player to remove.

		Returns:
			bool: True if the player was removed, False if not.
		"""
		return self.players.pop(user, None) is not None

	def get_player(self, user: str) -> Optional[User]:
		"""Retrieve a player from the lobby.

		Args:
			user (str): The username of the player to retrieve.

		Returns:
			Optional[User]: The User object representing the player, or None if not found.
		"""
		return self.players.get(user)

	def list_players(self) -> Iterable[User]:
		"""List all players in the lobby.

		Returns:
			Iterable[User]: An iterable of User objects representing all players.
		"""
		return self.players.values()

	def add_score(self, user: str, delta: int = 1) -> int:
		"""Add score to a player in the lobby.

		Args:
			user (str): The username of the player to add score to.
			delta (int, optional): The amount of score to add. Defaults to 1.

		Returns:
			int: The new score of the player.
		"""
		u = self.players.get(user)
		if u is None:
			raise ValueError(f"Player '{user}' not found in lobby.")
		return u.add_score(delta)

	# TODO Not used yet
	# def reset_all(self) -> None:
	# 	for u in self.players.values():
	# 		u.reset_score()

	def to_dict(self) -> dict:
		"""Convert the lobby to a dictionary representation for serialization in the response.

		Returns:
			dict: A dictionary containing lobby information.
		"""
		return {
			"id": self.id,
			"players": [ {"name": u.name, "score": u.score} for u in self.players.values() ],
			"playerCount": len(self.players),
			"scoreTotal": sum(u.score for u in self.players.values()),
		}