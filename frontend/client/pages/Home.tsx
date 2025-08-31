import React from "react";

/**
 * Home (root) page of the application.
 *
 * Keep page components in this directory. They should be *route-level* views
 * that compose smaller presentational / UI components from `../components`.
 */
export function HomePage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Starter Home Page</h1>
      <p className="text-muted-foreground">
        Replace this content with your app's landing experience. Create new
        route components in <code>client/pages</code> and add them to the
        router in <code>App.tsx</code>.
      </p>
    </div>
  );
}

export default HomePage;
