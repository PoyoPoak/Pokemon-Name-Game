import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from 'react-router-dom';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Placeholder set; backend will supply eventually
const DEFAULT_SET = Array.from({ length: 151 }, (_, i) => ({ index: i + 1, name: "" }));

interface GuessLogEntry {
  id: string;
  player: string;
  guess: string;
  result: "correct" | "duplicate" | "not_found" | "game_over" | "not_started" | "empty";
  at: number; // epoch ms
  positions?: number[];
}

export function GamePage() {
  const location = useLocation();
  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const lobbyId = params.get('lobby') || '';
  const playerName = params.get('player') || '';
  const [copied, setCopied] = useState(false);

  const [pokemonSet, setPokemonSet] = useState(DEFAULT_SET);
  const [guessedMap, setGuessedMap] = useState<Record<number, string>>({});
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false); // reflects server started & not paused & active
  const [paused, setPaused] = useState(false);
  const [started, setStarted] = useState(false);
  const [duration, setDuration] = useState(15 * 60); // seconds (updated from server)
  const [startTs, setStartTs] = useState<number | null>(null); // derived from server snapshot
  const [stateError, setStateError] = useState<string | null>(null);
  const lastServerRef = useRef<{ timeLeft: number; fetchedAt: number } | null>(null);
  const monotonicRef = useRef<number | null>(null); // never allow countdown to increase
  const [now, setNow] = useState(Date.now());
  const [log, setLog] = useState<GuessLogEntry[]>([]); // existing log; not focus per request
  const [guessError, setGuessError] = useState<string | null>(null);
  const submittingRef = useRef(false);
  const [players, setPlayers] = useState<{ name: string; score: number }[]>([]);
  const [playersError, setPlayersError] = useState<string | null>(null);

  // Poll lobby players
  useEffect(() => {
    if (!lobbyId) return;
    let cancelled = false;
    async function fetchPlayers() {
      try {
        const res = await fetch(`/api/games/${lobbyId}/players`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setPlayers(Array.isArray(data.players) ? data.players : []);
        setPlayersError(null);
      } catch (e: any) {
        if (!cancelled) setPlayersError(e.message || 'Failed to load players');
      }
    }
    fetchPlayers();
    const iv = setInterval(fetchPlayers, 3000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [lobbyId]);

  // Tick every second for countdown animation
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  // Poll game state (every 2s)
  useEffect(() => {
    if (!lobbyId) return;
    let cancelled = false;
    async function fetchState() {
      try {
        const res = await fetch(`/api/games/${lobbyId}/state`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
  const game = data.game || data.state || data; // flexible shape
  const lobby = data.lobby;
        if (game?.duration) setDuration(game.duration);
        const startedFlag = !!game?.started;
        const pausedFlag = !!game?.paused;
        if (typeof game?.timeLeft === 'number') {
          const serverLeft = game.timeLeft;
          const prev = monotonicRef.current;
          if (pausedFlag) {
            monotonicRef.current = serverLeft;
            lastServerRef.current = { timeLeft: serverLeft, fetchedAt: Date.now() };
          } else if (prev == null || serverLeft < prev || prev - serverLeft > 2) {
            monotonicRef.current = serverLeft;
            lastServerRef.current = { timeLeft: serverLeft, fetchedAt: Date.now() };
          } else if (lastServerRef.current) {
            lastServerRef.current.fetchedAt = Date.now();
          }
        }
        setPaused(pausedFlag);
  setStarted(startedFlag);
        setRunning(startedFlag && !pausedFlag && (game.timeLeft ?? 0) > 0);
        if (startedFlag && startTs == null && typeof game?.timeLeft === 'number') {
          // derive server startTs = now - (duration - timeLeft)
          setStartTs(Date.now() - (game.duration - game.timeLeft) * 1000);
        }
        setStateError(null);
        // integrate guessed map if provided
        if (game?.guessed && typeof game.guessed === 'object') {
          setGuessedMap(game.guessed);
        }
        // update players from lobby (authoritative) if present
        if (lobby && Array.isArray(lobby.players)) {
          setPlayers(lobby.players);
        }
        // sync shared log (convert server shape to GuessLogEntry)
        if (Array.isArray(game?.log)) {
          setLog(prev => {
            // Avoid re-adding identical sequence (simple length & last id heuristic)
            if (prev.length && game.log.length >= prev.length) {
              const lastPrev = prev[0];
              const lastNew = game.log[game.log.length - 1];
              if (lastPrev && lastNew && lastPrev.id === lastNew.id && game.log.length === prev.length) {
                return prev; // unchanged
              }
            }
            // Server log oldest->newest; we store newest first
            const mapped: GuessLogEntry[] = game.log.slice(-500).map((e: any) => ({
              id: e.id,
              player: e.player || '',
              guess: e.guess,
              result: e.accepted ? 'correct' : (e.reason || 'not_found'),
              at: Math.floor((e.ts || Date.now()) * 1000),
              positions: e.positions || []
            })).reverse();
            return mapped;
          });
        }
      } catch (e: any) {
        if (!cancelled) setStateError(e.message || 'Failed to fetch state');
      }
    }
    fetchState();
    const iv = setInterval(fetchState, 2000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [lobbyId, startTs]);

  const timeLeft = useMemo(() => {
    // Prefer server snapshot drifted by local elapsed since fetched
    if (!started) {
      // Pre-start: show full duration from server (no drift / countdown)
      if (lastServerRef.current) return lastServerRef.current.timeLeft;
      return duration;
    }
    if (paused) {
      // While paused, freeze at last monotonic value or snapshot
      if (monotonicRef.current != null) return monotonicRef.current;
      if (lastServerRef.current) return lastServerRef.current.timeLeft;
      return duration;
    }
    if (lastServerRef.current && monotonicRef.current != null) {
      const { timeLeft: snapshotLeft, fetchedAt } = lastServerRef.current;
      const drift = (now - fetchedAt) / 1000;
      const calc = Math.max(0, Math.ceil(snapshotLeft - drift));
      // Enforce monotonic non-increase
      if (calc <= monotonicRef.current) {
        monotonicRef.current = calc;
      }
      return monotonicRef.current;
    }
    if (!startTs) return duration;
    const elapsed = (now - startTs) / 1000;
    return Math.max(0, Math.ceil(duration - elapsed));
  }, [now, duration, startTs]);

  useEffect(() => {
    if (timeLeft === 0 && running) setRunning(false);
  }, [timeLeft, running]);

  const startGame = async () => {
    if (!lobbyId) return;
    try {
      const res = await fetch(`/api/games/${lobbyId}/start`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to start');
      const state = data.state || data.game || data;
      if (state?.duration) setDuration(state.duration);
      if (typeof state?.timeLeft === 'number') {
        lastServerRef.current = { timeLeft: state.timeLeft, fetchedAt: Date.now() };
        setStartTs(Date.now() - (state.duration - state.timeLeft) * 1000);
      }
  setPaused(false);
  setStarted(true);
  setRunning(true);
      setStateError(null);
    } catch (e: any) {
      setStateError(e.message || 'Start failed');
    }
  };

  const pauseGame = async () => {
    if (!lobbyId) return;
    try {
      const res = await fetch(`/api/games/${lobbyId}/pause`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to pause');
      const state = data.state || data.game || data;
      if (typeof state?.timeLeft === 'number') {
        lastServerRef.current = { timeLeft: state.timeLeft, fetchedAt: Date.now() };
      }
  setPaused(true);
  setRunning(false); // treat paused as not running for input disable
      setStateError(null);
    } catch (e: any) {
      setStateError(e.message || 'Pause failed');
    }
  };

  const guessedCount = Object.keys(guessedMap).length;
  const total = pokemonSet.length;

  // Format mm:ss
  const timeStr = useMemo(() => {
    const m = Math.floor(timeLeft / 60).toString().padStart(2, "0");
    const s = (timeLeft % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }, [timeLeft]);

  // Submit guess to backend
  const submitGuess = useCallback(async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!running || paused || timeLeft <= 0) return;
    const raw = input.trim();
    if (!raw || !lobbyId || !playerName) return;
    if (submittingRef.current) return; // simple in-flight guard
    submittingRef.current = true;
    setGuessError(null);
    try {
      const res = await fetch(`/api/games/${lobbyId}/guess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ guess: raw, player: playerName })
      });
      const data = await res.json();
      if (!res.ok || !data.accepted) {
        setGuessError(data.reason || 'rejected');
        if (data.event) {
          setLog(prev => [{
            id: data.event.id,
            player: data.event.player || playerName,
            guess: data.event.guess,
            result: data.event.accepted ? 'correct' : (data.event.reason || 'not_found'),
            at: Math.floor((data.event.ts || Date.now()) * 1000),
            positions: data.event.positions || []
          }, ...prev]);
        }
        return;
      }
      // Optimistically update guessedMap with user-entered name for returned positions
      if (Array.isArray(data.positions)) {
        setGuessedMap(g => {
          const next = { ...g };
          for (const pos of data.positions) {
            if (!next[pos]) next[pos] = raw; // will be replaced with canonical name on next poll
          }
          return next;
        });
      }
      // Update players scores if server provided
      if (Array.isArray(data.players)) {
        setPlayers(data.players);
      } else {
        // Fallback optimistic increment for the current player
        setPlayers(prev => prev.map(p => p.name === playerName ? { ...p, score: p.score + 1 } : p));
      }
      if (data.event) {
        setLog(prev => [{
          id: data.event.id,
          player: data.event.player || playerName,
          guess: data.event.guess,
          result: data.event.accepted ? 'correct' : (data.event.reason || 'not_found'),
          at: Math.floor((data.event.ts || Date.now()) * 1000),
          positions: data.event.positions || []
        }, ...prev]);
      }
    } catch (err: any) {
      setGuessError(err.message || 'network_error');
    } finally {
      submittingRef.current = false;
      setInput('');
    }
  }, [input, lobbyId, playerName, running, paused, timeLeft]);

  // Force exactly 4 columns regardless of set size
  const COLUMNS = 4;
  const perCol = Math.ceil(total / COLUMNS);
  const columnData = Array.from({ length: COLUMNS }, (_, col) => (
    pokemonSet.slice(col * perCol, (col + 1) * perCol)
  ));

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex-1 min-w-0">
          <form onSubmit={submitGuess} className="flex flex-col gap-4">
            <div className="flex flex-wrap items-end gap-4">
              <div className="flex-1 min-w-[240px] grid gap-2">
                <label htmlFor="guess" className="text-sm font-medium">Enter Pokémon species:</label>
                <Input
                  id="guess"
                  placeholder={running ? "Start typing..." : paused ? "Paused" : "Start the game first"}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  disabled={!running || timeLeft === 0 || submittingRef.current}
                />
                {guessError && <span className="text-[10px] text-destructive">{guessError}</span>}
              </div>
              {lobbyId && (
                <div className="flex flex-col items-center gap-1 self-end">
                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground text-center">Lobby Code</span>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      className="h-8 px-3 text-sm font-mono"
                      onClick={() => {
                        navigator.clipboard.writeText(lobbyId).then(() => {
                          setCopied(true);
                          setTimeout(() => setCopied(false), 1200);
                        });
                      }}
                    >
                      {lobbyId}
                    </Button>
                    {copied && <span className="text-xs text-green-600 dark:text-green-400">Copied</span>}
                  </div>
                </div>
              )}
              <div className="flex items-center gap-6">
                <div className="flex flex-col items-center text-center">
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">Score</div>
                  <div className="text-3xl font-semibold tabular-nums">{guessedCount}/{total}</div>
                </div>
                <div className="flex flex-col items-center">
                  <div className="flex items-center gap-3">
          {!running ? (
                      <Button
                        type="button"
                        variant='default'
                        onClick={startGame}
                        disabled={!lobbyId}
                        className="h-9 px-3"
                      >
            {startTs && paused ? 'Resume' : 'Start'}
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        variant='secondary'
                        onClick={pauseGame}
                        className="h-9 px-3"
                      >
                        Pause
                      </Button>
                    )}
                    <div className="flex flex-col items-center w-[80px] text-center">
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Remaining</span>
                      <span className="text-3xl font-semibold tabular-nums leading-none">{timeStr}</span>
                    </div>
                  </div>
                  {/* Give Up button removed per request */}
                  {stateError && <span className="mt-1 text-[10px] text-destructive">{stateError}</span>}
                </div>
              </div>
            </div>
            <div className="overflow-auto border rounded-md">
              <div className="grid text-sm grid-cols-4">
                {columnData.map((colArr, cIdx) => (
                  <div key={cIdx} className="border-l first:border-l-0">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr>
                          <th className="sticky top-0 bg-background border-b px-2 py-1 text-xs font-semibold">Dex</th>
                          <th className="sticky top-0 bg-background border-b px-2 py-1 text-xs font-semibold">Pokémon</th>
                        </tr>
                      </thead>
                      <tbody>
                        {colArr.map(p => {
                          const name = guessedMap[p.index];
                          return (
                            <tr key={p.index} className={cn("border-b last:border-b-0 h-6", name && "bg-primary/10") }>
                              <td className="px-2 py-0.5 align-middle tabular-nums w-12 text-muted-foreground">{p.index.toString().padStart(3,'0')}</td>
                              <td className="px-2 py-0.5 align-middle font-medium">{name || ''}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            </div>
          </form>
        </div>
        <div className="w-full lg:w-80 xl:w-96 flex flex-col gap-2">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-base">Lobby Players</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 px-2 pb-2">
              <ul className="max-h-48 overflow-auto divide-y rounded-md bg-background/60 text-sm">
                {players.length === 0 && !playersError && (
                  <li className="px-4 py-2 text-xs text-muted-foreground">No players yet.</li>
                )}
                {playersError && (
                  <li className="px-4 py-2 text-xs text-destructive">{playersError}</li>
                )}
                {players.map(p => (
                  <li key={p.name} className="px-4 py-2 flex items-center justify-between gap-3">
                    <span className="font-medium truncate">{p.name}</span>
                    <span className="text-xs tabular-nums text-muted-foreground">{p.score}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
          <Card className="flex-1 min-h-[400px]">
            <CardHeader className="py-3 px-6">
              <CardTitle className="text-base">Game Log</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 pb-4 px-6">
              <ul className="text-sm max-h-[600px] overflow-auto divide-y -mx-6 px-6 pb-1">
                {log.length === 0 && (
                  <li className="py-2 text-muted-foreground text-xs">No guesses yet. Guesses will appear here.</li>
                )}
                {log.map(entry => (
                  <li key={entry.id} className="py-2 flex items-start gap-2">
                    <span className="text-xs tabular-nums text-muted-foreground w-14">{new Date(entry.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                    <span className="font-semibold">{entry.player}</span>
                    <span className="flex-1 break-words">{entry.guess}</span>
                    <span className={cn("text-xs font-medium px-1.5 py-0.5 rounded", entry.result === 'correct' ? 'bg-green-500/20 text-green-700 dark:text-green-300' : entry.result === 'duplicate' ? 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300' : 'bg-red-500/20 text-red-700 dark:text-red-300')}>{entry.result}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default GamePage;
