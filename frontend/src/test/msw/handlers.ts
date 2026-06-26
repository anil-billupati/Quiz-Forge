/**
 * MSW request handlers — contract-shaped mocks of the ContestForge REST API.
 *
 * These let the UI team build and test against the API contract
 * (docs/spec/api-contracts.yaml) BEFORE the backend endpoint exists. Once
 * `npm run generate:api` produces `src/types/api.gen.ts`, tighten the response
 * bodies to the generated `components["schemas"][...]` types.
 *
 * Keep these in sync at the per-feature "contract freeze" (ways-of-working doc).
 */
import { http, HttpResponse } from "msw";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const url = (p: string) => `${BASE}${p}`;

const ok = <T>(body: T, status = 200) => HttpResponse.json(body as never, { status });
const err = (code: string, message: string, status: number, details = {}) =>
  HttpResponse.json({ error: { code, message, details } }, { status });

export const handlers = [
  // ── Auth ──────────────────────────────────────────────────────────────
  http.post(url("/auth/login"), async ({ request }) => {
    const body = (await request.json()) as { email?: string };
    if (!body?.email) return err("BAD_REQUEST", "email required", 400);
    return ok({
      access_token: "mock.access.jwt",
      refresh_token: "mock.refresh.jwt",
      token_type: "bearer",
      expires_in: 900,
      role: "ORG_ADMIN",
    });
  }),
  http.get(url("/auth/me"), () =>
    ok({
      id: "00000000-0000-0000-0000-000000000001",
      tenant_id: "00000000-0000-0000-0000-0000000000aa",
      email: "admin@acme.test",
      first_name: "Asha",
      last_name: "Rao",
      role: "ORG_ADMIN",
      status: "ACTIVE",
      created_at: new Date().toISOString(),
    }),
  ),
  http.post(url("/auth/logout"), async ({ request }) => {
    const body = (await request.json()) as { refresh_token?: string };
    if (!body?.refresh_token) return err("UNAUTHORIZED", "refresh_token required", 401);
    return new HttpResponse(null, { status: 204 });
  }),
  http.post(url("/auth/change-password"), () => new HttpResponse(null, { status: 204 })),

  // ── Users: bulk import (F5) ─────────────────────────────────────────────
  http.post(url("/users/bulk"), async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get("file");
    if (!(file instanceof File)) return err("UNPROCESSABLE", "no file", 422);
    const text = await file.text();
    const rows = text
      .split("\n")
      .slice(1)
      .filter((line) => line.trim());
    if (rows.length === 0) return err("UNPROCESSABLE", "no rows", 422);
    const results = rows.map((line, i) => {
      const [email] = line.split(",");
      const cleanEmail = email?.trim() ?? "";
      return cleanEmail.includes("dup")
        ? { email: cleanEmail, status: "SKIPPED", reason: "duplicate_email", user_id: null, one_time_password: null }
        : {
            email: cleanEmail,
            status: "CREATED",
            reason: null,
            user_id: `00000000-0000-0000-0000-0000000010${String(i).padStart(2, "0")}`,
            one_time_password: `Otp-${Math.random().toString(36).slice(2, 8)}`,
          };
    });
    return ok({
      created_count: results.filter((r) => r.status === "CREATED").length,
      skipped_count: results.filter((r) => r.status === "SKIPPED").length,
      results,
    });
  }),

  // ── Contests ────────────────────────────────────────────────────────────
  http.get(url("/contests"), () =>
    ok({
      items: [
        {
          id: "00000000-0000-0000-0000-0000000000c1",
          name: "Fresher Hiring Challenge",
          description: "Multi-round",
          structure: "GROUPED",
          lifecycle_status: "REGISTRATION_OPEN",
          scheduled_start_at: null,
          group_score_rollup: "SUM",
          rollup_best_n: null,
          created_at: new Date().toISOString(),
        },
      ],
      next_cursor: null,
      has_more: false,
    }),
  ),

  // ── Questions: bulk CSV import ──────────────────────────────────────────
  http.post(url("/contests/:id/questions/bulk"), async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get("file");
    if (!(file instanceof File)) return err("UNPROCESSABLE", "file required", 422);
    const text = await file.text();
    const rows = text.split("\n").slice(1).filter((line) => line.trim());
    if (rows.length === 0) return err("UNPROCESSABLE", "empty csv", 422);
    const imported = rows.map((line, i) => ({
      id: `00000000-0000-0000-0000-000000000q${i + 1}`,
      tenant_id: "00000000-0000-0000-0000-0000000000aa",
      contest_id: "contest",
      group_id: null,
      sequence: i + 1,
      text: line.split(",")[1]?.trim() ?? `Question ${i + 1}`,
      explanation: null,
      options: [
        { id: `opt-${i}-a`, text: "Option A", is_correct: true, ordinal: 0 },
        { id: `opt-${i}-b`, text: "Option B", is_correct: false, ordinal: 1 },
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));
    return ok(imported, 201);
  }),

  // ── Registrations ───────────────────────────────────────────────────────
  http.post(url("/contests/:id/registrations"), ({ params }) =>
    ok({
      id: "00000000-0000-0000-0000-0000000000r1",
      tenant_id: "00000000-0000-0000-0000-0000000000aa",
      contest_id: params.id,
      participant_id: "00000000-0000-0000-0000-0000000000p1",
      status: "REGISTERED",
      spectator_access: false,
      joined_at: null,
      final_rank: null,
      final_score: null,
      registered_at: new Date().toISOString(),
    }, 201)
  ),
  http.get(url("/contests/:id/registrations"), ({ params }) =>
    ok([
      {
        id: "00000000-0000-0000-0000-0000000000r1",
        tenant_id: "00000000-0000-0000-0000-0000000000aa",
        contest_id: params.id,
        participant_id: "00000000-0000-0000-0000-0000000000p1",
        status: "REGISTERED",
        spectator_access: false,
        joined_at: null,
        final_rank: null,
        final_score: null,
        registered_at: new Date().toISOString(),
      },
    ])
  ),
  http.get(url("/contests/:id/registrations/me"), ({ params }) =>
    ok({
      id: "00000000-0000-0000-0000-0000000000r1",
      tenant_id: "00000000-0000-0000-0000-0000000000aa",
      contest_id: params.id,
      participant_id: "00000000-0000-0000-0000-0000000000p1",
      status: "REGISTERED",
      spectator_access: false,
      joined_at: null,
      final_rank: null,
      final_score: null,
      registered_at: new Date().toISOString(),
    })
  ),
  http.delete(url("/contests/:id/registrations/:registrationId"), () => new HttpResponse(null, { status: 204 })),

  // ── Live: ticket + reconnect snapshot ───────────────────────────────────
  http.post(url("/contests/:id/live-ticket"), () => ok({ ticket: "mock-ticket-123", expires_in: 30 })),
  http.get(url("/contests/:id/live-state"), ({ params }) =>
    ok({
      contest_id: params.id,
      phase: "SUBMISSION",
      current_question: {
        id: "00000000-0000-0000-0000-0000000000q1",
        sequence: 1,
        text: "What is 2 + 2?",
        options: [
          { id: "opt-a", text: "3", ordinal: 1 },
          { id: "opt-b", text: "4", ordinal: 2 },
          { id: "opt-c", text: "5", ordinal: 3 },
        ],
      },
      submission_close_at: new Date(Date.now() + 20_000).toISOString(),
      status: "ACTIVE",
      score: 30,
    })
  ),

  // ── Moderator controls ──────────────────────────────────────────────────
  http.post(url("/contests/:id/control/start"), ({ params }) =>
    ok({
      contest_id: params.id,
      phase: "DISPLAY",
      current_group_id: null,
      current_question_id: "00000000-0000-0000-0000-0000000000q1",
      current_sequence: 1,
      submission_close_at: null,
      version: 1,
      started_at: new Date().toISOString(),
    })
  ),
  http.post(url("/contests/:id/control/reveal"), ({ params }) =>
    ok({
      contest_id: params.id,
      phase: "SUBMISSION",
      current_group_id: null,
      current_question_id: "00000000-0000-0000-0000-0000000000q1",
      current_sequence: 1,
      submission_close_at: new Date(Date.now() + 20_000).toISOString(),
      version: 2,
      started_at: new Date().toISOString(),
    })
  ),
  http.post(url("/contests/:id/control/advance"), ({ params }) =>
    ok({
      contest_id: params.id,
      phase: "DISPLAY",
      current_group_id: null,
      current_question_id: "00000000-0000-0000-0000-0000000000q2",
      current_sequence: 2,
      submission_close_at: null,
      version: 3,
      started_at: new Date().toISOString(),
    })
  ),

  // ── Ops / health ────────────────────────────────────────────────────────
  http.get(url("/health"), () => ok({ status: "ok" })),
  http.get(url("/ready"), () =>
    ok({ status: "ready", dependencies: { postgres: "ok", redis: "ok" } })
  ),

  // ── Leaderboard (REST fallback for the WS push) ─────────────────────────
  // NOTE: This endpoint is spec-ahead. The backend leaderboard router is not
  // implemented yet (Unit 12), so no production frontend code should call it.
  http.get(url("/contests/:id/leaderboard"), () =>
    ok([
      { participant_id: "p1", display_name: "Arjun", rank: 1, score: 100, total_time_ms: 4200, wrong_count: 0, last_correct_at: null },
      { participant_id: "p2", display_name: "Bina", rank: 1, score: 100, total_time_ms: 5100, wrong_count: 0, last_correct_at: null },
      { participant_id: "p3", display_name: "Chen", rank: 3, score: 75, total_time_ms: 3000, wrong_count: 1, last_correct_at: null },
    ]),
  ),
];
