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
  result: "pending" | "correct" | "duplicate" | "not_found";
  at: number; // epoch ms
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
  const [running, setRunning] = useState(false);
  const [duration] = useState(15 * 60); // seconds (configurable later)
  const [startTs, setStartTs] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const [log, setLog] = useState<GuessLogEntry[]>([]);
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

  // Timer effect
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [running]);

  const timeLeft = useMemo(() => {
    if (!startTs) return duration;
    const elapsed = (now - startTs) / 1000;
    return Math.max(0, Math.ceil(duration - elapsed));
  }, [startTs, now, duration]);

  useEffect(() => {
    if (timeLeft === 0 && running) setRunning(false);
  }, [timeLeft, running]);

  const toggleTimer = () => {
    if (running) {
      setRunning(false);
    } else {
      const firstStart = startTs == null;
      if (firstStart) setStartTs(Date.now());
      setRunning(true);
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

  // Handle local guess submission (mock evaluation only)
  const submitGuess = useCallback((e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const raw = input.trim();
    if (!raw) return;
    const normalized = raw.toLowerCase();
    // Mock: consider any non-empty unique guess as correct until full integration
    const already = Object.values(guessedMap).some(g => g === normalized);
    const entry: GuessLogEntry = {
      id: crypto.randomUUID(),
      player: "you", // later: actual player
      guess: raw,
      result: already ? "duplicate" : "correct",
      at: Date.now()
    };
  // Uncapped log (scrollable container). Consider pruning server-side later.
  setLog(prev => [entry, ...prev]);
    if (!already) {
      // Assign next empty slot in set
      const empty = pokemonSet.find(p => !guessedMap[p.index]);
      if (empty) {
        setGuessedMap(g => ({ ...g, [empty.index]: raw }));
      }
    }
    setInput("");
  }, [input, guessedMap, pokemonSet]);

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
                  placeholder="Start typing..."
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  disabled={!running || timeLeft === 0}
                />
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
                    <Button type="button" variant={running ? 'secondary' : 'default'} onClick={toggleTimer} className="h-9 px-3">
                      {running ? 'Pause' : 'Start'}
                    </Button>
                    <div className="flex flex-col items-center w-[80px] text-center">
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Remaining</span>
                      <span className="text-3xl font-semibold tabular-nums leading-none">{timeStr}</span>
                    </div>
                  </div>
                  {/* Give Up button removed per request */}
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
            <CardHeader className="py-3">
              <CardTitle className="text-base">Game Log</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="text-sm max-h-[600px] overflow-auto divide-y">
                {log.length === 0 && (
                  <li className="p-3 text-muted-foreground text-xs">No guesses yet. Guesses will appear here.</li>
                )}
                {log.map(entry => (
                  <li key={entry.id} className="px-3 py-2 flex items-start gap-2">
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
