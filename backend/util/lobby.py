"""Game module. Provides a minimal in‑memory Game container that tracks `User` instances and game variables."""

from __future__ import annotations
from typing import Dict, Iterable, Optional
from util.user import User

class Lobby:
	def __init__(self, id: str):
		self.id = id	
		self.score = 0
		self.players: Dict[str, User] = {} 

	def add_player(self, user: str) -> User:
		if user in self.players:
			raise ValueError(f"Username '{user}' already exists; choose a different name.")
		u = User(user)
		self.players[user] = u
		return u

	def remove_player(self, user: str) -> bool:
		return self.players.pop(user, None) is not None

	def get_player(self, user: str) -> Optional[User]:
		return self.players.get(user)

	def list_players(self) -> Iterable[User]:
		return self.players.values()

	def add_score(self, user: str, delta: int = 1) -> int:
		u = self.add_player(user)
		return u.add_score(delta)

	def reset_all(self) -> None:
		for u in self.players.values():
			u.reset_score()

	def to_dict(self) -> dict:
		return {
			"id": self.id,
			"players": [ {"name": u.name, "score": u.score} for u in self.players.values() ],
			"playerCount": len(self.players),
			"scoreTotal": sum(u.score for u in self.players.values()),
		}