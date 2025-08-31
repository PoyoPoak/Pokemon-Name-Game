import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
// Global styles (Tailwind + base application styles)
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(<App />);