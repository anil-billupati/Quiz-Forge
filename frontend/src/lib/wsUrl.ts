/**
 * Build the backend WebSocket URL for a contest live channel.
 *
 * Next.js API routes cannot proxy WebSocket, so the browser connects directly
 * to the backend after exchanging a short-lived ticket over REST.
 */

export function getWsBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";
  return base.replace(/\/$/, "");
}

export function buildLiveWsUrl(contestId: string): string {
  return `${getWsBaseUrl()}/contests/${contestId}/live`;
}
