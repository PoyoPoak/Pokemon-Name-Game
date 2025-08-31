import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

/**
 * Home (root) page of the application.
 *
 * Keep page components in this directory. They should be *route-level* views
 * that compose smaller presentational / UI components from `../components`.
 */
export function HomePage({ className }: { className?: string }) {
  const [mode, setMode] = useState<"create" | "join">("create");
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [pending, setPending] = useState(false);
  const [preview, setPreview] = useState<any | null>(null); // keep for debug display
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      let resp: Response;
      if (mode === 'create') {
        resp = await fetch('/api/games', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username })
        });
      } else {
        resp = await fetch(`/api/games/${code}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
      }
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.error || 'Request failed');
      } else {
        setPreview(data); // debug
        const lobbyId = data.lobbyId || code;
        // Navigate to game page with query params for future state fetching
        navigate(`/game?lobby=${encodeURIComponent(lobbyId)}&player=${encodeURIComponent(username)}`);
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setPending(false);
    }
  }

  const disabled = !username || (mode === 'join' && !code) || pending;

  return (
    <div className={cn("flex flex-col gap-6 max-w-sm mx-auto pt-16", className)}>
      <Card>
        <CardHeader>
          <CardTitle>{mode === 'create' ? 'Create a Game' : 'Join a Game'}</CardTitle>
          <CardDescription>
            {mode === 'create' ? 'Choose a username to host a new lobby.' : 'Enter a lobby code to join your friends.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="flex flex-col gap-6">
            <div className="grid gap-3">
              <Label htmlFor="username">Username</Label>
              <Input id="username" value={username} onChange={e => setUsername(e.target.value)} required />
            </div>
            {mode === 'join' && (
              <div className="grid gap-3">
                <Label htmlFor="code">Lobby Code</Label>
                <Input id="code" value={code} onChange={e => setCode(e.target.value)} required />
              </div>
            )}
            <div className="flex flex-col gap-3">
              <div className="flex gap-2">
                <Button type="button" variant={mode === 'create' ? 'default' : 'outline'} onClick={() => setMode('create')} className="w-full">Create</Button>
                <Button type="button" variant={mode === 'join' ? 'default' : 'outline'} onClick={() => setMode('join')} className="w-full">Join</Button>
              </div>
              <Button type="submit" disabled={disabled} className="w-full">
                {pending ? 'Please wait...' : (mode === 'create' ? 'Create Lobby' : 'Join Lobby')}
              </Button>
            </div>
            {error && <div className="text-xs rounded-md bg-destructive/10 text-destructive p-2">{error}</div>}
            {preview && (
              <div className="text-xs rounded-md bg-muted/50 p-3 font-mono whitespace-pre-wrap">
                {JSON.stringify(preview, null, 2)}
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default HomePage;
