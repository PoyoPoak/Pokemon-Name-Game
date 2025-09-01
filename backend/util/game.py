"""Game controller: maintains game state, timer, and guess processing.

High‑level responsibilities:
	* Manage a single lobby's timed session (start, pause/resume, restart).
	* Track which Pokémon have been guessed (by Pokédex position) and which remain.
	* Perform normalization / cleaning of user guesses and resolve to one or more positions.
	* Produce compact (`summary`) and detailed (`detailed_state`) serializable views for APIs.

Current implementation is **in‑memory** (process‑local) and meant for early development.
Future enhancements (out of scope here):
	* External persistence (Redis / database) for horizontal scaling & durability.
	* Pub/Sub or WS/SSE pushing instead of client polling.
	* Per‑player scoring & attribution (only raw guess acceptance handled now).
"""

from __future__ import annotations

import time
import re
from typing import Dict, List, Set

from data.pokemon_data import GENERATION_1


def _clean_name(name: str) -> str:
	"""Normalize a Pokémon name / user guess for comparison.

	Steps:
		* Remove any non‑alphabetic characters.
		* Lowercase.
		* Strip surrounding whitespace.
	This allows accepting variations like "Mr. Mime" vs "mrmime".
	"""
	return re.sub(r"[^a-zA-Z]", "", name).lower().strip()


class Game:
	"""Single lobby game instance.

	Timing model:
		* When created, the game is "not started"; `time_left` reports full duration.
		* `start()` sets `started = True` and establishes `ends_at`.
		* `pause()` captures remaining seconds in `paused_remaining` and nulls `ends_at`.
		* Resuming (calling `start()` while paused) recalculates a new `ends_at` based on
			the stored remaining seconds.
		* If the game finished (timer hit 0 or all Pokémon guessed), a subsequent `start()`
			acts as a full restart (guesses cleared).

	Guess model:
		* `remaining` maps position -> canonical name still unguessed.
		* `guessed` maps position -> canonical name guessed.
		* `guessed_clean` stores cleaned (normalized) forms to quickly reject duplicates.
		* `clean_to_positions` precomputes which Pokédex positions share the same cleaned
			token (covers edge cases of alternate forms / spacing, though Gen 1 is simple).
	"""

	def __init__(self, lobby_id: str, duration_seconds: int = 15 * 60):
		# Identifiers / metadata
		self.lobby_id = lobby_id
		self.duration_seconds = duration_seconds  # total allotted time for session
		self.created_at = time.time()

		# Timing state
		self.started = False          # Has the game ever been started? (affects restart logic)
		self.paused = False           # Currently paused flag
		self.started_at: float | None = None  # Wall time when (last) started/resumed
		self.ends_at: float | None = None     # Wall time when current run should end
		self.paused_remaining: int | None = None  # Seconds remaining captured at pause

		# Pokémon data (Gen 1 full list). For a future multi‑gen mode, original_list could vary.
		self.original_list: List[str] = GENERATION_1

		# Dynamic collections partition original_list into remaining vs guessed positions.
		self.remaining: Dict[int, str] = {i + 1: n for i, n in enumerate(self.original_list)}
		self.guessed: Dict[int, str] = {}
		self.guessed_clean: Set[str] = set()

		# Mapping from cleaned token -> list of positions (handles multi‑form names or variants).
		self.clean_to_positions: Dict[str, List[int]] = {}
		for pos, name in self.remaining.items():
			cleaned = _clean_name(name)
			self.clean_to_positions.setdefault(cleaned, []).append(pos)

		# Shared guess log (list of dict events). Truncated to a max length when appended.
		self.log: List[dict] = []
		self.max_log_entries = 500

	# ------------------------------------------------------------------
	# Core timing
	# ------------------------------------------------------------------
	def time_left(self) -> int:
		"""Return remaining time (integer seconds) respecting pause & pre‑start states.

		Priority order:
		  1. If paused, return the frozen `paused_remaining` snapshot.
		  2. If never started (or ends_at cleared), report full duration.
		  3. Otherwise, compute `ends_at - now` clamped at >= 0.
		"""
		if self.paused and self.paused_remaining is not None:
			return self.paused_remaining
		if not self.started or self.ends_at is None:
			return self.duration_seconds
		return max(0, int(self.ends_at - time.time()))

	def is_active(self) -> bool:
		"""Whether the game is currently running (started, not paused, time > 0)."""
		return self.started and (not self.paused) and self.time_left() > 0

	def start(self) -> str:
		"""Start, resume, or restart the game.

		Returns one of:
		  * 'started'        – first time starting.
		  * 'already_started'– already running (no state change).
		  * 'resumed'        – unpaused with remaining time restored.
		  * 'restarted'      – had ended (time or completion) and was fully reset.
		"""
		if self.started and self.paused:
			remaining = self.paused_remaining if self.paused_remaining is not None else self.duration_seconds
			self.started_at = time.time()
			self.ends_at = self.started_at + remaining
			self.paused = False
			self.paused_remaining = None
			return 'resumed'
		if self.started and self.is_active():
			return 'already_started'
		if self.started and not self.is_active():
			self._reset_state()
			status = 'restarted'
		else:
			status = 'started'
		self.started = True
		self.started_at = time.time()
		self.ends_at = self.started_at + self.duration_seconds
		return status

	def pause(self) -> str:
		"""Pause the game (freeze timer) capturing remaining seconds.

		Returns:
		  * 'not_started'     – cannot pause before first start.
		  * 'already_paused'  – idempotent.
		  * 'already_finished'– game already ended (time or completion).
		  * 'paused'          – success.
		"""
		if not self.started:
			return 'not_started'
		if self.paused:
			return 'already_paused'
		if not self.is_active(): 
			return 'already_finished'
		self.paused_remaining = self.time_left()
		self.paused = True
  
		# Clear ends_at to reduce accidental misuse (resume reconstructs it).
		self.ends_at = None
		return 'paused'

	# ------------------------------------------------------------------
	# Guess handling
	# ------------------------------------------------------------------
	def submit_guess(self, player: str, raw_guess: str) -> Dict[str, object]:
		"""Handle a user guess with validation & logging.

		Returns result dict (accepted flag, metadata) plus logs the attempt.
		"""
		if not self.started:
			return self._log_event(player, raw_guess, {"accepted": False, "reason": "not_started"})
		if not self.is_active():
			return self._log_event(player, raw_guess, {"accepted": False, "reason": "game_over"})

		guess_clean = _clean_name(raw_guess)
		if not guess_clean:
			return self._log_event(player, raw_guess, {"accepted": False, "reason": "empty"})
		if guess_clean in self.guessed_clean:
			return self._log_event(player, raw_guess, {"accepted": False, "reason": "duplicate"})

		positions = self.clean_to_positions.get(guess_clean)
		if not positions:
			return self._log_event(player, raw_guess, {"accepted": False, "reason": "not_found"})

		accepted_positions: List[int] = []
		for pos in positions:
			if pos in self.guessed:
				continue
			name = self.remaining.get(pos)
			if name:
				self.guessed[pos] = name
				self.remaining.pop(pos, None)
				accepted_positions.append(pos)

		self.guessed_clean.add(guess_clean)
		total = len(self.guessed)
		done = total >= len(self.original_list)
		if done:
			self.ends_at = time.time()

		result = {
			"accepted": True,
			"positions": accepted_positions,
			"normalized": guess_clean,
			"totalGuessed": total,
			"remaining": len(self.original_list) - total,
			"complete": done,
		}
		return self._log_event(player, raw_guess, result)

	# ------------------------------------------------------------------
	# State / serialization
	# ------------------------------------------------------------------
	def summary(self) -> Dict[str, object]:
		"""Compact state used by most polling endpoints."""
		return {
			"lobbyId": self.lobby_id,
			"duration": self.duration_seconds,
			"timeLeft": self.time_left(),
			"total": len(self.original_list),
			"guessedCount": len(self.guessed),
			"isActive": self.is_active(),
			"started": self.started,
			"paused": self.paused,
		}

	def detailed_state(self) -> Dict[str, object]:
		"""Expanded state including full guessed mapping and shared log."""
		return {
			**self.summary(),
			"guessed": self.guessed,  # {position: name}
			"log": list(self.log),
		}
	# ------------------------------------------------------------------
	# Reset / admin
	# ------------------------------------------------------------------
	def reset(self) -> None:
		"""Hard reset: reconstruct object while retaining lobby id & duration."""
		self.__init__(self.lobby_id, self.duration_seconds)

	def _reset_state(self) -> None:
		"""Internal partial reset (used for full game restart without reallocation)."""
		self.remaining = {i + 1: n for i, n in enumerate(self.original_list)}
		self.guessed = {}
		self.guessed_clean = set()
		self.clean_to_positions = {}
		for pos, name in self.remaining.items():
			cleaned = _clean_name(name)
			self.clean_to_positions.setdefault(cleaned, []).append(pos)
		self.log.clear()

	def _log_event(self, player: str, raw_guess: str, result: Dict[str, object]) -> Dict[str, object]:
		"""Internal helper: append an event to shared log and return enriched result.

		Event shape: {id, ts, player, guess, accepted, reason?, positions?}
		"""
		import uuid  # local import to avoid module-level cost if unused
		entry = {
			"id": uuid.uuid4().hex,
			"ts": time.time(),
			"player": player or "",
			"guess": raw_guess,
			"accepted": bool(result.get("accepted")),
			"reason": result.get("reason"),
			"positions": result.get("positions", []),
		}
		self.log.append(entry)
		if len(self.log) > self.max_log_entries:
			# Keep most recent entries
			self.log = self.log[-self.max_log_entries:]
		# Return result including the event for immediate client consumption
		result_with_event = dict(result)
		result_with_event["event"] = entry
		return result_with_event


# Global in‑memory registry of games (lobby_id -> Game)
GAMES: Dict[str, Game] = {}


def get_or_create_game(lobby_id: str, duration_seconds: int = 15 * 60) -> Game:
	"""Fetch existing game for lobby or create a new one with given duration.

	Duration parameter only applies if creating a new instance.
	"""
	game = GAMES.get(lobby_id)
	if game is None:
		game = Game(lobby_id, duration_seconds)
		GAMES[lobby_id] = game
	return game


__all__ = ["Game", "GAMES", "get_or_create_game"]