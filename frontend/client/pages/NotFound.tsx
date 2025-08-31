import React from "react";

/**
 * Generic 404 page shown for any unmatched route.
 */
export function NotFoundPage() {
  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-2">404 - Not Found</h1>
      <p>The page you requested does not exist yet.</p>
    </div>
  );
}

export default NotFoundPage;
