import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Route-level pages
import HomePage from "@/pages/Home";
import NotFoundPage from "@/pages/NotFound";
import GamePage from "@/pages/Game";

// Example shared UI component (remove once you add real components)
import { Placeholder } from "@/components/ui/Placeholder";

// A single QueryClient instance for React Query data caching.
const queryClient = new QueryClient();

/**
 * App root component.
 *
 * Responsibilities here:
 *  - Provide top-level context providers (React Query, Theme, Auth, etc.)
 *  - Configure the router & layout wrappers
 *  - Should avoid feature business logic
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="game" element={<GamePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
