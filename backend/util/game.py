"""Game controller: maintains game state, timer, and guess processing.

This is an in‑memory implementation suitable for early development.
Later: persist to Redis / DB + push updates via WS/SSE.
"""

from __future__ import annotations

import time
import re
from typing import Dict, List, Set

from data.pokemon_data import GENERATION_1


def _clean_name(name: str) -> str:
	return re.sub(r"[^a-zA-Z]", "", name).lower().strip()


class Game:
	"""Single lobby game instance."""

	def __init__(self, lobby_id: str, duration_seconds: int = 15 * 60):
		self.lobby_id = lobby_id
		self.duration_seconds = duration_seconds
		self.created_at = time.time()
		self.started = False
		self.started_at: float | None = None
		self.ends_at: float | None = None

		# Pokemon data
		self.original_list: List[str] = GENERATION_1
		self.remaining: Dict[int, str] = {i + 1: n for i, n in enumerate(self.original_list)}
		self.guessed: Dict[int, str] = {}
		self.guessed_clean: Set[str] = set()
		self.clean_to_positions: Dict[str, List[int]] = {}
		for pos, name in self.remaining.items():
			cleaned = _clean_name(name)
			self.clean_to_positions.setdefault(cleaned, []).append(pos)

	# ------------------------------------------------------------------
	# Core timing
	# ------------------------------------------------------------------
	def time_left(self) -> int:
		if not self.started or self.ends_at is None:
			return self.duration_seconds
		return max(0, int(self.ends_at - time.time()))

	def is_active(self) -> bool:
		return self.started and self.time_left() > 0

	def start(self) -> str:
		"""Start or restart the game.

		Returns a status string: 'started', 'already_started', or 'restarted'.
		If previously ended, this will reset guesses and start fresh.
		"""
		if self.started and self.is_active():
			return 'already_started'
		if self.started and not self.is_active():
			# treat as restart (reset state first)
			self._reset_state()
			status = 'restarted'
		else:
			status = 'started'
		self.started = True
		self.started_at = time.time()
		self.ends_at = self.started_at + self.duration_seconds
		return status

	# ------------------------------------------------------------------
	# Guess handling
	# ------------------------------------------------------------------
	def submit_guess(self, player: str, raw_guess: str) -> Dict[str, object]:
		if not self.started:
			return {"accepted": False, "reason": "not_started"}
		if not self.is_active():
			return {"accepted": False, "reason": "game_over"}
		guess_clean = _clean_name(raw_guess)
		if not guess_clean:
			return {"accepted": False, "reason": "empty"}
		if guess_clean in self.guessed_clean:
			return {"accepted": False, "reason": "duplicate"}

		positions = self.clean_to_positions.get(guess_clean)
		if not positions:
			return {"accepted": False, "reason": "not_found"}

		accepted_positions: List[int] = []
		for pos in positions:
			if pos in self.guessed:
				continue  # already filled by earlier multi‑form guess
			name = self.remaining.get(pos)
			if name:
				self.guessed[pos] = name
				self.remaining.pop(pos, None)
				accepted_positions.append(pos)

		self.guessed_clean.add(guess_clean)
		total = len(self.guessed)
		done = total >= len(self.original_list)
		if done:
			self.ends_at = time.time()  # end immediately

		return {
			"accepted": True,
			"positions": accepted_positions,
			"normalized": guess_clean,
			"totalGuessed": total,
			"remaining": len(self.original_list) - total,
			"complete": done,
		}

	# ------------------------------------------------------------------
	# State / serialization
	# ------------------------------------------------------------------
	def summary(self) -> Dict[str, object]:
		return {
			"lobbyId": self.lobby_id,
			"duration": self.duration_seconds,
			"timeLeft": self.time_left(),
			"total": len(self.original_list),
			"guessedCount": len(self.guessed),
			"isActive": self.is_active(),
			"started": self.started,
		}

	def detailed_state(self) -> Dict[str, object]:
		return {
			**self.summary(),
			"guessed": self.guessed,  # {position: name}
		}

	# ------------------------------------------------------------------
	# Reset / admin
	# ------------------------------------------------------------------
	def reset(self) -> None:
		self.__init__(self.lobby_id, self.duration_seconds)

	def _reset_state(self) -> None:
		# internal: only reset guess-related structures
		self.remaining = {i + 1: n for i, n in enumerate(self.original_list)}
		self.guessed = {}
		self.guessed_clean = set()
		self.clean_to_positions = {}
		for pos, name in self.remaining.items():
			cleaned = _clean_name(name)
			self.clean_to_positions.setdefault(cleaned, []).append(pos)


# Global in‑memory registry of games (lobby_id -> Game)
GAMES: Dict[str, Game] = {}


def get_or_create_game(lobby_id: str, duration_seconds: int = 15 * 60) -> Game:
	game = GAMES.get(lobby_id)
	if game is None:
		game = Game(lobby_id, duration_seconds)
		GAMES[lobby_id] = game
	return game


__all__ = ["Game", "GAMES", "get_or_create_game"]