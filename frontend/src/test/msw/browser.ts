/**
 * MSW worker for the browser (local UI dev against mocks, no backend needed).
 *
 * Enable in a client entrypoint (dev only), e.g.:
 *   if (process.env.NEXT_PUBLIC_API_MOCK === "1") {
 *     const { worker } = await import("@/test/msw/browser");
 *     await worker.start({ onUnhandledRequest: "bypass" });
 *   }
 * Run `npx msw init public/ --save` once to emit the service worker file.
 */
import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);
