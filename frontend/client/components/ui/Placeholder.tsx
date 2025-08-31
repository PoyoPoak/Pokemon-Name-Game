import React from "react";

/**
 * Example UI component.
 *
 * Put *reusable, presentation-focused* components under `client/components`.
 * Avoid coupling them to routing or data fetching; pass data via props so
 * they stay easy to reuse and test.
 */
export interface PlaceholderProps {
  label?: string;
}

export const Placeholder: React.FC<PlaceholderProps> = ({ label = "Placeholder" }) => {
  return (
    <div className="rounded border border-dashed p-4 text-sm text-gray-500">
      {label}
    </div>
  );
};
