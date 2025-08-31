import express from "express";
import path from "path";

const app = express();
app.use(express.json());

app.get("/api/ping", (_req, res) => res.json({ message: "pong" }));

// Serve built SPA when deployed (dist should contain index.html)
const distPath = path.join(process.cwd(), "dist");
app.use(express.static(distPath));

app.get("*", (req, res) => {
  if (req.path.startsWith("/api")) return res.status(404).json({ error: "Not found" });
  res.sendFile(path.join(distPath, "index.html"));
});

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Server listening on ${port}`));