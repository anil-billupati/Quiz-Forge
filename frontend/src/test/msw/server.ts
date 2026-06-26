/**
 * MSW server for Node test environments (vitest, integration tests).
 * Usage in a test setup file:
 *   import { server } from "@/test/msw/server";
 *   beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
 *   afterEach(() => server.resetHandlers());
 *   afterAll(() => server.close());
 */
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
