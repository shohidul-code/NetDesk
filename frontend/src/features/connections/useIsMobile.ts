import { useSyncExternalStore } from "react";

const QUERY = "(max-width: 639px)"; // Tailwind's sm breakpoint: tables become cards, drawers slide from the bottom

function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(QUERY);
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

export function useIsMobile(): boolean {
  return useSyncExternalStore(subscribe, () => window.matchMedia(QUERY).matches, () => false);
}
