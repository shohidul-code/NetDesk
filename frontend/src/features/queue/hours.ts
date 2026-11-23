/** Whole hours a complaint has been open. A finished one stops counting at its last update. */
export function hoursOpen(createdAt: string, status: string, updatedAt: string, now: number): number {
  const end = status === "resolved" || status === "closed" ? Date.parse(updatedAt) : now;
  return Math.max(0, Math.floor((end - Date.parse(createdAt)) / 3_600_000));
}
