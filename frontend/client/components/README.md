Components Directory
====================

Guidelines:

1. Place *reusable* presentational or small stateful widgets here.
2. Group by domain or UI category when it grows (e.g. `auth/`, `charts/`).
3. Keep route-level views in `../pages` — they compose these building blocks.
4. Keep hooks in a future `../hooks` directory (e.g. `useUser`, `useFeatureFlag`).
5. Co-locate component-specific styles (CSS / modules) next to the component if needed.

Subfolders:
 - `ui/` for generic primitives (buttons, inputs, placeholders, etc.)
 - more domain or feature folders can be added later.
