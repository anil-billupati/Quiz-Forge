# ContestForge — Domain Model

| | |
|---|---|
| **Project** | ContestForge |
| **Source** | docs/spec/product-spec.md, docs/spec/technical-spec.md |
| **Date** | 2026-06-22 |
| **Status** | Draft v0.3 — merged (HEAD + main) |

---

## 1. Bounded Contexts

ContestForge has five cohesive sub-domains within one service:

1. **Tenancy & Identity** — `Organization`, `TenantSettings`, `User`, `RefreshToken`, roles,
   authentication.
2. **Contest Authoring** — `Contest`, `Group`, `ConfigurationBlock`, `WildcardConfig`, `Question`,
   `Option`.
3. **Live Execution & Scoring** — `Registration`, `ContestExecutionState`, `QuestionWindow`,
   `AnswerSubmission`, `Score`, `WildcardActivation`, `LeaderboardEntry`.
4. **Elimination** — `Checkpoint`, `EliminationRule`, `EliminationEvent`.
5. **Platform Cross-Cutting** — `OutboxEvent`, `Notification`, `AuditLog`, `ContestLifecycleEvent`,
   `TenantUsageRecord`, `ParticipantScoreSummary`, `ContestResultSnapshot` (durable messaging,
   participant notifications, audit trail, operational metrics, and derived/recoverable state).

All tenant-scoped entities carry `tenant_id` (the `Organization` id). `User` with role
`SUPER_ADMIN` is platform-scoped (`tenant_id` is null). Composite foreign keys include `tenant_id`
to enforce isolation at the database level.

**Primary key convention:** UUIDv7 is used for all primary keys to improve write locality on
high-insert tables (`AnswerSubmission`, `Score`, etc.).

---

## 2. Core Entities

### Tenancy & Identity

**Organization (Tenant)**
- `id` (UUIDv7, PK)
- `slug` (string, unique, not null, 3–64 chars, lowercase alphanumeric + hyphen) — tenant key;
  used as the login `tenant_slug` and as the subdomain label (e.g. `acme`)
- `name` (string)
- `portal_url` (string, unique, not null) — canonical tenant portal URL
  (e.g. `https://acme.contestforge.com`)
- `custom_domain` (string, unique, nullable) — optional vanity/white-label domain
  (e.g. `quiz.acme.edu`)
- `status` (enum: ACTIVE | SUSPENDED)
- `settings` (JSONB) — tenant-level defaults and feature flags
- `created_by` (User id — Super Admin, nullable platform reference)
- `created_at`, `updated_at` (timestamp)
- *Unique:* `slug`, `portal_url`, `custom_domain`

**TenantSettings** *(tenant-level configuration; one row per Organization)*
- `organization_id` (UUIDv7, PK, FK → Organization)
- `max_concurrent_live_contests` (int, default 5)
- `max_participants_per_contest` (int, default 10_000)
- `max_questions_per_contest` (int, default 200)
- `default_negative_marking` (boolean, default false)
- `updated_at` (timestamp)

**User**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization; null only for SUPER_ADMIN)
- `email` (string, not null)
- `password_hash` (string)
- `role` (enum: SUPER_ADMIN | ORG_ADMIN | MODERATOR | PARTICIPANT)
- `first_name` (string, not null)
- `last_name` (string, not null)
- `email_verified_at` (timestamp, nullable)
- `status` (enum: ACTIVE | DISABLED)
- `created_at`, `updated_at`
- *Unique:* `(tenant_id, email)` where `tenant_id` is not null.
- *Partial unique:* `(email)` where `role = SUPER_ADMIN` (platform-wide unique).

**RefreshToken** *(JWT refresh rotation — FR-4)*
- `id` (UUIDv7, PK)
- `user_id` (UUID, FK → User)
- `tenant_id` (UUID, FK → Organization; null for SUPER_ADMIN)
- `token_hash` (string — hashed, never stored in plaintext)
- `token_family` (UUID — links rotated refresh tokens)
- `issued_at`, `expires_at` (timestamp)
- `revoked_at` (timestamp, nullable)
- `replaced_by` (UUID, FK → RefreshToken, nullable — set on rotation)
- *Index:* `(user_id, token_family)` for rotation validation.

---

### Contest Authoring

**Contest**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `name`, `description` (string)
- `structure` (enum: NORMAL | GROUPED)
- `lifecycle_status` (enum: DRAFT | PUBLISHED | REGISTRATION_OPEN |
  REGISTRATION_CLOSED | SCHEDULED | LIVE | COMPLETED | ARCHIVED)
- `scheduled_start_at` (timestamp, nullable)
- `group_score_rollup` (enum: SUM | WEIGHTED_SUM | BEST_N; Grouped only)
- `rollup_best_n` (int, nullable; when BEST_N)
- `created_by` (User id), `created_at`, `updated_at`
- *FK:* `(tenant_id, created_by)` references `User(tenant_id, id)` for tenant-scoped
  creators; Super Admin-created tenants use a nullable platform reference.
- *Index:* `(tenant_id, lifecycle_status)` for tenant contest listing.

**Group** (Grouped contests only)
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `name` (string)
- `sequence` (int — run order)
- `weight` (decimal, nullable; for WEIGHTED_SUM)
- *FK:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`
- *Unique:* `(tenant_id, contest_id, sequence)`

**ConfigurationBlock**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest, nullable) — set when scope = CONTEST (Normal)
- `group_id` (UUID, FK → Group, nullable) — set when scope = GROUP (Grouped)
- `mode` (enum: STANDARD | SPEED | ELIMINATION)
- `question_duration_s` (int, 5–300)
- `question_interval_s` (int, 0–60)
- `explanation_duration_s` (int, 0–60)
- `leaderboard_duration_s` (int, 0–60)
- `reveal_mode` (enum: AUTOMATIC | MODERATOR_CONTROLLED)
- `ranking_criterion` (enum: SCORE_ONLY | SCORE_TIME | ACCURACY)
- `tie_display` (enum: SHARED_RANK | FASTEST | LEAST_INCORRECT)
- `leaderboard_visibility` (enum: ALWAYS | POST_QUESTION | HIDDEN | MASKED)
- `update_frequency` (enum: PER_ANSWER | PER_QUESTION | PER_GROUP)
- `elimination_combine_operator` (enum: AND | OR, nullable) — single top-level
  operator combining all of the block's EliminationRules (ELIMINATION mode only)
- `survivor_score_reset` (boolean, default false) — when true, survivors' scores
  reset at the start of the next group instead of carrying forward (FR-37)
- **Scoring config (derived by mode):**
  - `correct_points` (int, default 10; Fixed)
  - `wrong_points` (int, default 0; may be negative; Fixed)
  - `second_chance_rate` (decimal, default 0.5)
  - `time_bands` (array; Speed) or `decay` `{max_points, floor, decay_rate}` (Speed)
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, group_id)` references `Group(tenant_id, id)`
- *CHECK:* exactly one of (`contest_id`, `group_id`) is not null.
- *Partial unique:* `(tenant_id, contest_id)` where `group_id` is null;
  `(tenant_id, group_id)` where `contest_id` is null.

**WildcardConfig** *(per ConfigurationBlock — FR-26)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `config_block_id` (UUID, FK → ConfigurationBlock)
- `type` (enum: FIFTY_FIFTY | SECOND_CHANCE | SKIP)
- `usage_limit` (int — max uses per participant per quiz/group)
- `eligibility` (string — e.g. `ALL` | `TOP_50_PERCENT`)
- `cooldown_questions` (int — minimum questions between same-wildcard uses)
- `carry_over` (boolean — whether the wildcard carries to the next group or
  resets; Grouped only)
- *FK:* `(tenant_id, config_block_id)` references `ConfigurationBlock(tenant_id, id)`
- *Constraint:* unique `(tenant_id, config_block_id, type)` — at most one config per
  wildcard type per block.

**Question**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `group_id` (UUID, FK → Group, nullable; Grouped)
- `sequence` (int)
- `text` (string)
- `explanation` (string, nullable)
- `created_at`, `updated_at`
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, group_id)` references `Group(tenant_id, id)`
- *Partial unique:* `(tenant_id, contest_id, sequence)` where `group_id` is null;
  `(tenant_id, group_id, sequence)` where `group_id` is not null.
- *Note:* runtime reveal timing is recorded per run in **QuestionWindow**, not on the
  authored question. `Question` does **not** have a `reveal_at` field.

**Option**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `question_id` (UUID, FK → Question)
- `text` (string)
- `is_correct` (boolean)
- `ordinal` (int)
- *FK:* `(tenant_id, question_id)` references `Question(tenant_id, id)`
- *Unique:* `(tenant_id, question_id, ordinal)`
- *Partial unique:* `(tenant_id, question_id)` where `is_correct = true`
  (exactly one correct option per question).

---

### Live Execution & Scoring

**ContestExecutionState** *(durable live-execution state — recovery, FR-42/NFR-6)*
- `contest_id` (UUIDv7, PK, FK → Contest) — singleton per contest
- `tenant_id` (UUID, FK → Organization)
- `current_group_id` (UUID, FK → Group, nullable)
- `current_question_id` (UUID, FK → Question, nullable)
- `phase` (enum: DISPLAY | SUBMISSION | EVALUATION | EXPLANATION | LEADERBOARD |
  INTERVAL | BETWEEN_GROUPS | ENDED)
- `version` (int) — optimistic lock
- `started_at`, `updated_at` (timestamp)
- *FK:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`
- *Purpose:* the single durable source the Execution Engine reads on restart to
  resume a Live contest without loss or double-progression.

**QuestionWindow** *(authoritative server-side timing per question run)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `group_id` (UUID, FK → Group, nullable)
- `question_id` (UUID, FK → Question)
- `sequence` (int)
- `revealed_at` (timestamp, nullable — when the question was revealed)
- `submission_close_at` (timestamp — authoritative close time; FR-20)
- `evaluated_at` (timestamp, nullable)
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, group_id)` references `Group(tenant_id, id)`;
  `(tenant_id, question_id)` references `Question(tenant_id, id)`
- *Unique:* `(tenant_id, contest_id, question_id)`. This is the authority for
  accepting/rejecting late answers and for recovering open windows after a crash.
- *Index:* `(tenant_id, contest_id, sequence)` for ordered recovery.

**Registration**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `participant_id` (UUID, FK → User)
- `status` (enum: REGISTERED | ACTIVE | ELIMINATED | COMPLETED)
- `joined_at` (timestamp, nullable — when the participant joined the Live run)
- `spectator_access` (boolean, default false — view-only access after
  elimination, FR-37)
- `final_rank` (int, nullable — set at contest completion)
- `final_score` (int, nullable — set at contest completion)
- `registered_at` (timestamp)
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, participant_id)` references `User(tenant_id, id)`
- *Unique:* `(tenant_id, contest_id, participant_id)`
- *Index:* `(tenant_id, contest_id, status)`

**AnswerSubmission** *(durable answer record — durability boundary)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id`, `question_id`, `participant_id` (UUID, FKs)
- `question_window_id` (UUID, FK → QuestionWindow — the authoritative window
  this submission was evaluated against)
- `attempt_no` (int; 1 = first, 2 = Second Chance)
- `selected_option_id` (UUID, FK → Option, nullable for skip/timeout)
- `server_accepted_at` (timestamp — authoritative scoring time, FR-40)
- `response_time_ms` (int — from reveal to accept; for Speed/tie-break)
- `outcome` (enum: CORRECT | WRONG | TIMEOUT | SKIPPED)
- `idempotency_hash` (UUID — deterministic hash of `contest_id|question_id|participant_id|attempt_no`)
- `idempotency_debug` (string — human-readable form of the idempotency inputs)
- `scored` (boolean, default false) — set true once the Score row is written
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, question_id)` references `Question(tenant_id, id)`;
  `(tenant_id, participant_id)` references `User(tenant_id, id)`;
  `(tenant_id, question_window_id)` references `QuestionWindow(tenant_id, id)`;
  `(tenant_id, selected_option_id)` references `Option(tenant_id, id)`
- *Unique:* `(tenant_id, idempotency_hash)`
- *Index:* `(tenant_id, contest_id, question_id, participant_id, attempt_no)`
- *Partitioning:* by `HASH(contest_id)` into 64 partitions.

**Score**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `group_id` (UUID, FK → Group, nullable)
- `question_id` (UUID, FK → Question) — denormalized for audit
- `participant_id` (UUID, FK → User)
- `answer_submission_id` (UUID, FK → AnswerSubmission)
- `scoring_model` (enum: FIXED | TIME_BASED) — denormalized for audit
- `points` (int)
- `scored_at` (timestamp)
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, group_id)` references `Group(tenant_id, id)`;
  `(tenant_id, question_id)` references `Question(tenant_id, id)`;
  `(tenant_id, participant_id)` references `User(tenant_id, id)`;
  `(tenant_id, answer_submission_id)` references `AnswerSubmission(tenant_id, id)`
- *Unique:* `(tenant_id, answer_submission_id)`
- *Index:* `(tenant_id, contest_id, participant_id)`
- *Partitioning:* by `HASH(contest_id)` into 64 partitions (aligned with AnswerSubmission).

**WildcardActivation**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `question_id` (UUID, FK → Question)
- `participant_id` (UUID, FK → User)
- `type` (enum: FIFTY_FIFTY | SECOND_CHANCE | SKIP)
- `activated_at` (timestamp)
- `outcome` (JSONB — e.g. `{ "removed_options": [...], "points_effect": ... }`)
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, question_id)` references `Question(tenant_id, id)`;
  `(tenant_id, participant_id)` references `User(tenant_id, id)`

**LeaderboardEntry** *(materialized/cached in Redis; rebuildable)*
- Redis key namespace: `tenant:{tenant_id}:contest:{contest_id}:group:{group_id}:view:{view}`
- `participant_id`
- `score`, `total_time_ms`, `wrong_count`, `last_correct_at`
- `rank`

---

### Elimination

**EliminationRule**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `config_block_id` (UUID, FK → ConfigurationBlock)
- `type` (enum: FIRST_WRONG | N_WRONG | BOTTOM_X_PERCENT | MIN_SCORE)
- `n_value` (int, nullable; N_WRONG, default 3)
- `percent_value` (decimal, nullable; BOTTOM_X_PERCENT)
- `min_score` (int, nullable; MIN_SCORE)
- *FK:* `(tenant_id, config_block_id)` references `ConfigurationBlock(tenant_id, id)`
- *Note:* how multiple rules combine is set once at the block level via
  `ConfigurationBlock.elimination_combine_operator` (AND | OR), not per rule.

**Checkpoint**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `config_block_id` (UUID, FK → ConfigurationBlock)
- `type` (enum: AFTER_QUESTION | AFTER_GROUP | CUSTOM_MILESTONE)
- `question_sequence` (int, nullable; AFTER_QUESTION)
- `milestone_at` (timestamp, nullable; CUSTOM_MILESTONE)
- *FK:* `(tenant_id, config_block_id)` references `ConfigurationBlock(tenant_id, id)`

**EliminationEvent**
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `participant_id` (UUID, FK → User)
- `checkpoint_id` (UUID, FK → Checkpoint)
- `final_rank` (int), `final_score` (int)
- `eliminated_at` (timestamp)
- `spectator_granted` (boolean)
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, participant_id)` references `User(tenant_id, id)`;
  `(tenant_id, checkpoint_id)` references `Checkpoint(tenant_id, id)`
- *Unique:* `(tenant_id, contest_id, participant_id)`

---

### Platform Cross-Cutting

**OutboxEvent** *(transactional outbox — durable, at-least-once messaging)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization, nullable for platform events)
- `aggregate_type` (string — e.g. `AnswerSubmission`, `Contest`)
- `aggregate_id` (UUID — id of the originating entity)
- `event_type` (string — e.g. `answer.accepted`, `checkpoint.reached`)
- `payload` (jsonb)
- `status` (enum: PENDING | PROCESSED | DEAD_LETTER)
- `created_at` (timestamp), `processed_at` (timestamp, nullable)
- *Index:* `(status, created_at)` partial `WHERE status = 'PENDING'`
- *Purpose:* events are written in the same transaction as the state change and
  relayed to engine workers/notifications, giving at-least-once delivery and
  reconciliation after a crash (technical-spec command channel).

**Notification** *(participant-facing — FR-37, FR-41)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `participant_id` (UUID, FK → User)
- `type` (enum: ELIMINATION | ANSWER_ACK | SPECTATOR_GRANTED | CONTEST_PROGRESS)
- `payload` (jsonb — e.g. final rank/score for ELIMINATION)
- `created_at` (timestamp), `delivered_at` (timestamp, nullable)
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, participant_id)` references `User(tenant_id, id)`

**AuditLog** *(audit trail — technical-spec §6)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization, nullable for platform-level actions
  such as org create/suspend)
- `actor_user_id` (UUID, FK → User)
- `action` (string — e.g. `org.create`, `contest.lifecycle.transition`,
  `tiebreak.resolved`, `participant.eliminated`)
- `entity_type` (string), `entity_id` (UUID)
- `metadata` (jsonb)
- `created_at` (timestamp)
- *FK:* `(actor_user_id)` references `User(id)`

**ContestLifecycleEvent** *(audit log of contest status transitions)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `previous_status` (enum lifecycle status)
- `new_status` (enum lifecycle status)
- `triggered_by` (User id, FK → User)
- `metadata` (JSONB, nullable)
- `created_at` (timestamp)
- *FK:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`
- *Index:* `(tenant_id, contest_id, created_at)`

**TenantUsageRecord** *(periodic aggregate; foundation for billing and capacity planning)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `period_start`, `period_end` (timestamp)
- `contests_created` (int)
- `live_contest_peak` (int)
- `participant_minutes` (bigint)
- `questions_created` (int)
- `answer_submissions` (int)
- `wildcard_activations` (int)
- `storage_bytes` (bigint)
- `updated_at` (timestamp)

**ParticipantScoreSummary** *(derived aggregate; rebuildable from Score)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest)
- `group_id` (UUID, FK → Group, nullable)
- `participant_id` (UUID, FK → User)
- `total_score` (int)
- `total_response_time_ms` (int)
- `wrong_count` (int)
- `last_correct_at` (timestamp, nullable)
- `updated_at` (timestamp)
- *FKs:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`;
  `(tenant_id, group_id)` references `Group(tenant_id, id)`;
  `(tenant_id, participant_id)` references `User(tenant_id, id)`
- *Unique:* `(tenant_id, contest_id, group_id, participant_id)`
- *Note:* This table is derived from `Score` and `AnswerSubmission`. It exists
  to speed up leaderboard computation and rebuilds; cache loss does not affect
  it because it can be recomputed from authoritative data (FR-44).

**ContestResultSnapshot** *(immutable final ranking written on Archive)*
- `id` (UUIDv7, PK)
- `tenant_id` (UUID, FK → Organization)
- `contest_id` (UUID, FK → Contest, unique)
- `snapshot` (JSONB — ordered list of `{ participant_id, rank, score, ... }`)
- `created_at` (timestamp)
- *FK:* `(tenant_id, contest_id)` references `Contest(tenant_id, id)`
- *Unique:* `(tenant_id, contest_id)`

---

## 3. Physical Database Design

### 3.1 Tenant isolation strategy

- **Application-enforced:** every repository query includes `tenant_id` filter
  via a SQLAlchemy mixin; unscoped queries fail closed in production.
- **Database-enforced:** composite foreign keys include `tenant_id` so a row
  cannot reference a parent in another tenant even if a bug injects the wrong ID.
- **Defense in depth:** optional PostgreSQL Row-Level Security (RLS) policies
  enforce `tenant_id` filtering at the database level.
- **Super Admin:** platform-scoped users operate outside tenant filters but
  cannot mutate tenant data without explicit tenant context.

### 3.2 Indexing strategy

Hot-path indexes:

- `organization` — unique `slug`, unique `portal_url`, unique `custom_domain`.
- `tenant_settings` — PK on `organization_id`.
- `user` — partial unique `(tenant_id, email)` where `tenant_id` is not null;
  partial unique `(email)` where `role = 'SUPER_ADMIN'`.
- `contest` — `(tenant_id, lifecycle_status)`.
- `configuration_block` — partial unique `(tenant_id, contest_id)` where `group_id` is null;
  partial unique `(tenant_id, group_id)` where `contest_id` is null.
- `wildcard_config` — unique `(tenant_id, config_block_id, type)`.
- `group` — unique `(tenant_id, contest_id, sequence)`.
- `question` — partial unique `(tenant_id, contest_id, sequence)` where `group_id` is null;
  partial unique `(tenant_id, group_id, sequence)` where `group_id` is not null.
- `option` — unique `(tenant_id, question_id, ordinal)`;
  partial unique `(tenant_id, question_id)` where `is_correct = true`.
- `contest_execution_state` — PK on `contest_id`.
- `question_window` — unique `(tenant_id, contest_id, question_id)`;
  index `(tenant_id, contest_id, sequence)`.
- `registration` — unique `(tenant_id, contest_id, participant_id)`;
  index `(tenant_id, contest_id, status)`.
- `answer_submission` — unique `(tenant_id, idempotency_hash)`;
  index `(tenant_id, contest_id, question_id, participant_id, attempt_no)`;
  index `(tenant_id, contest_id, scored)` for recovery re-drive.
- `score` — unique `(tenant_id, answer_submission_id)`;
  index `(tenant_id, contest_id, participant_id)`.
- `participant_score_summary` — unique
  `(tenant_id, contest_id, group_id, participant_id)`.
- `outbox_event` — partial index `(status, created_at)` where `status = 'PENDING'`.
- `contest_lifecycle_event` — index `(tenant_id, contest_id, created_at)`.

### 3.3 Partitioning strategy

- `answer_submission` is partitioned by `HASH(contest_id)` into 64 partitions
  to spread write load during high-concurrency contests.
- `score` is co-partitioned by `HASH(contest_id)` into 64 partitions so joins
  between `answer_submission` and `score` stay partition-local.
- `participant_score_summary` may be partitioned by `HASH(contest_id)` if
  leaderboard rebuild latency becomes a bottleneck.

### 3.4 High-write optimizations

- **UUIDv7 PKs** improve index locality over random UUIDv4 on high-insert tables.
- **`server_accepted_at`** is set by a PostgreSQL trigger using
  `clock_timestamp()` to guarantee monotonic, authoritative timestamps.
- **Idempotency** uses a deterministic UUID hash instead of a string concatenation
  for fast equality checks and smaller index size.
- **Batch upserts** are used when rebuilding `participant_score_summary` from
  `Score` rows after cache loss or recovery.
- **Connection pooling** via asyncpg/SQLAlchemy (min 10 / max 100 per instance);
  PgBouncer in transaction-pooling mode if needed.
- **Synchronous commit** remains the default for answer writes; the durability
  boundary is the PostgreSQL commit before the client ack.

### 3.5 Enum representation

- PostgreSQL native `ENUM` types for low-cardinality, stable enums
  (`lifecycle_status`, `role`, `mode`, `outcome`, etc.).
- `smallint` with Python enum mapping may be used for the hottest tables
  (`answer_submission`, `score`) if benchmarked as faster; migration path is
  a simple column cast.

### 3.6 Archival strategy

- `Archived` is a lifecycle status, not a separate table. No data migration
  occurs on archive.
- `ContestResultSnapshot` is written once when a contest enters `Archived`
  to provide an immutable final ranking without recomputation.
- Historical `answer_submission` and `score` partitions may be detached after
  a tenant-configurable retention period (post-MVP).
- `contest_lifecycle_event` and `wildcard_activation` audit data are retained
  for 1 year.

---

## 4. Entity Relationship Diagram

```mermaid
erDiagram
    ORGANIZATION ||--o| TENANT_SETTINGS : has
    ORGANIZATION ||--o{ USER : has
    ORGANIZATION ||--o{ CONTEST : owns
    ORGANIZATION ||--o{ OUTBOX_EVENT : publishes
    ORGANIZATION ||--o{ AUDIT_LOG : audits
    ORGANIZATION ||--o{ TENANT_USAGE_RECORD : tracks

    USER ||--o{ CONTEST : creates
    USER ||--o{ REFRESH_TOKEN : has
    USER ||--o{ AUDIT_LOG : acts
    USER ||--o{ REGISTRATION : participates
    USER ||--o{ ANSWER_SUBMISSION : submits
    USER ||--o{ SCORE : earns
    USER ||--o{ WILDCARD_ACTIVATION : activates
    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ PARTICIPANT_SCORE_SUMMARY : summarized

    CONTEST ||--o{ GROUP : may_have
    CONTEST ||--o| CONFIGURATION_BLOCK : normal_block
    CONTEST ||--o{ QUESTION : contains
    CONTEST ||--|| CONTEST_EXECUTION_STATE : live_state
    CONTEST ||--o{ QUESTION_WINDOW : runs
    CONTEST ||--o{ REGISTRATION : has
    CONTEST ||--o{ ANSWER_SUBMISSION : receives
    CONTEST ||--o{ SCORE : generates
    CONTEST ||--o{ WILDCARD_ACTIVATION : sees
    CONTEST ||--o{ ELIMINATION_EVENT : eliminates
    CONTEST ||--o{ NOTIFICATION : emits
    CONTEST ||--o{ CONTEST_LIFECYCLE_EVENT : logs
    CONTEST ||--|| CONTEST_RESULT_SNAPSHOT : final
    CONTEST ||--o{ PARTICIPANT_SCORE_SUMMARY : summarizes

    GROUP ||--|| CONFIGURATION_BLOCK : grouped_block
    GROUP ||--o{ QUESTION : contains
    GROUP ||--o{ QUESTION_WINDOW : windows
    GROUP ||--o{ SCORE : grouped_scores
    GROUP ||--o{ PARTICIPANT_SCORE_SUMMARY : grouped_summary

    CONFIGURATION_BLOCK ||--o{ WILDCARD_CONFIG : enables
    CONFIGURATION_BLOCK ||--o{ ELIMINATION_RULE : defines
    CONFIGURATION_BLOCK ||--o{ CHECKPOINT : defines

    QUESTION ||--|{ OPTION : has
    QUESTION ||--o{ QUESTION_WINDOW : timed_by
    QUESTION ||--o{ ANSWER_SUBMISSION : answered_by
    QUESTION ||--o{ WILDCARD_ACTIVATION : on
    QUESTION ||--o{ SCORE : scored

    OPTION ||--o{ ANSWER_SUBMISSION : selected

    QUESTION_WINDOW ||--o{ ANSWER_SUBMISSION : scoped_by

    ANSWER_SUBMISSION ||--|| SCORE : yields

    CHECKPOINT ||--o{ ELIMINATION_EVENT : produces
    REGISTRATION ||--o{ ELIMINATION_EVENT : eliminated_in

    ORGANIZATION {
        uuid id PK
        string slug UK
        string name
        string portal_url UK
        string custom_domain UK
        enum status
        jsonb settings
        uuid created_by FK
    }
    TENANT_SETTINGS {
        uuid organization_id PK, FK
        int max_concurrent_live_contests
        int max_participants_per_contest
        int max_questions_per_contest
        boolean default_negative_marking
    }
    USER {
        uuid id PK
        uuid tenant_id FK
        string email
        string first_name
        string last_name
        enum role
        enum status
    }
    REFRESH_TOKEN {
        uuid id PK
        uuid user_id FK
        uuid tenant_id FK
        string token_hash
        uuid token_family
        timestamp issued_at
        timestamp expires_at
        timestamp revoked_at
        uuid replaced_by FK
    }
    CONTEST {
        uuid id PK
        uuid tenant_id FK
        string name
        enum structure
        enum lifecycle_status
        timestamp scheduled_start_at
        enum group_score_rollup
        int rollup_best_n
        uuid created_by FK
    }
    CONTEST_EXECUTION_STATE {
        uuid contest_id PK, FK
        uuid tenant_id FK
        uuid current_group_id FK
        uuid current_question_id FK
        enum phase
        int version
        timestamp updated_at
    }
    CONTEST_LIFECYCLE_EVENT {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        enum previous_status
        enum new_status
        uuid triggered_by FK
        timestamp created_at
    }
    CONTEST_RESULT_SNAPSHOT {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        jsonb snapshot
        timestamp created_at
    }
    GROUP {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        int sequence
        string name
        decimal weight
    }
    CONFIGURATION_BLOCK {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid group_id FK
        enum mode
        int question_duration_s
        int question_interval_s
        int explanation_duration_s
        int leaderboard_duration_s
        enum reveal_mode
        enum ranking_criterion
        enum tie_display
        enum leaderboard_visibility
        enum update_frequency
        enum elimination_combine_operator
        boolean survivor_score_reset
        jsonb scoring_config
    }
    WILDCARD_CONFIG {
        uuid id PK
        uuid tenant_id FK
        uuid config_block_id FK
        enum type
        int usage_limit
        string eligibility
        int cooldown_questions
        boolean carry_over
    }
    QUESTION {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid group_id FK
        int sequence
        string text
        string explanation
    }
    OPTION {
        uuid id PK
        uuid tenant_id FK
        uuid question_id FK
        string text
        boolean is_correct
        int ordinal
    }
    QUESTION_WINDOW {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid group_id FK
        uuid question_id FK
        int sequence
        timestamp revealed_at
        timestamp submission_close_at
        timestamp evaluated_at
    }
    REGISTRATION {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid participant_id FK
        enum status
        timestamp joined_at
        boolean spectator_access
        int final_rank
        int final_score
        timestamp registered_at
    }
    ANSWER_SUBMISSION {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid question_id FK
        uuid participant_id FK
        uuid question_window_id FK
        int attempt_no
        uuid selected_option_id FK
        timestamp server_accepted_at
        int response_time_ms
        enum outcome
        uuid idempotency_hash
        string idempotency_debug
        boolean scored
    }
    SCORE {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid group_id FK
        uuid question_id FK
        uuid participant_id FK
        uuid answer_submission_id FK
        enum scoring_model
        int points
        timestamp scored_at
    }
    WILDCARD_ACTIVATION {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid question_id FK
        uuid participant_id FK
        enum type
        timestamp activated_at
        jsonb outcome
    }
    LEADERBOARD_ENTRY {
        string redis_key
        uuid participant_id
        int score
        int total_time_ms
        int wrong_count
        timestamp last_correct_at
        int rank
    }
    ELIMINATION_RULE {
        uuid id PK
        uuid tenant_id FK
        uuid config_block_id FK
        enum type
        int n_value
        decimal percent_value
        int min_score
    }
    CHECKPOINT {
        uuid id PK
        uuid tenant_id FK
        uuid config_block_id FK
        enum type
        int question_sequence
        timestamp milestone_at
    }
    ELIMINATION_EVENT {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid participant_id FK
        uuid checkpoint_id FK
        int final_rank
        int final_score
        timestamp eliminated_at
        boolean spectator_granted
    }
    OUTBOX_EVENT {
        uuid id PK
        uuid tenant_id FK
        string aggregate_type
        uuid aggregate_id
        string event_type
        jsonb payload
        enum status
        timestamp created_at
        timestamp processed_at
    }
    NOTIFICATION {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid participant_id FK
        enum type
        jsonb payload
        timestamp created_at
        timestamp delivered_at
    }
    AUDIT_LOG {
        uuid id PK
        uuid tenant_id FK
        uuid actor_user_id FK
        string action
        string entity_type
        uuid entity_id
        jsonb metadata
        timestamp created_at
    }
    PARTICIPANT_SCORE_SUMMARY {
        uuid id PK
        uuid tenant_id FK
        uuid contest_id FK
        uuid group_id FK
        uuid participant_id FK
        int total_score
        int total_response_time_ms
        int wrong_count
        timestamp last_correct_at
        timestamp updated_at
    }
    TENANT_USAGE_RECORD {
        uuid id PK
        uuid tenant_id FK
        timestamp period_start
        timestamp period_end
        int contests_created
        int live_contest_peak
        bigint participant_minutes
        int questions_created
        int answer_submissions
        int wildcard_activations
        bigint storage_bytes
        timestamp updated_at
    }
```

> `OUTBOX_EVENT` and `AUDIT_LOG` are intentionally loosely coupled (referenced
> by `aggregate_id` / `entity_id` rather than hard FKs) so they can record
> events across any aggregate without coupling the write path to every table.

---

## 5. Business Rules

- **BR-1 (Tenant isolation):** Every tenant-scoped query is filtered by
  `tenant_id`; no entity may reference another tenant's entity. Composite FKs
  include `tenant_id` so the database enforces this even if application filters
  fail. (FR-3)
- **BR-2 (Structure ↔ config placement):** Normal → exactly one
  ConfigurationBlock at contest scope; Grouped → exactly one ConfigurationBlock
  per Group. (FR-8)
- **BR-3 (Mode → scoring):** STANDARD and ELIMINATION ⇒ Fixed scoring; SPEED ⇒
  Time-Based. Scoring model is derived from `mode` and is never set independently.
  (FR-12)
- **BR-4 (Elimination requires rules):** ELIMINATION mode blocks must have ≥1
  EliminationRule, ≥1 Checkpoint, and a non-null
  `elimination_combine_operator` (AND | OR) that combines all of the block's
  rules; non-ELIMINATION blocks ignore them. (FR-10, FR-33, FR-34)
- **BR-5 (Lifecycle monotonicity):** `lifecycle_status` advances only through the
  fixed sequence; no skipping. Structure locks at `PUBLISHED`; ConfigurationBlock
  locks at `REGISTRATION_OPEN`. (FR-7, FR-9)
- **BR-6 (Config field ranges):** Durations honor PRD bounds (question 5–300s;
  interval/explanation/leaderboard 0–60s). Other numeric bounds (points, rates,
  percentages) are validated on write. (FR-10)
- **BR-7 (Authoritative timestamp):** `AnswerSubmission.server_accepted_at` is
  set once, at first server acceptance, by a database trigger using
  `clock_timestamp()`; it is the scoring/tie-break time even after retries.
  (FR-40)
- **BR-8 (At-most-once scoring):** `Score.answer_submission_id` is unique; a
  given AnswerSubmission yields exactly one Score. (FR-39)
- **BR-9 (Late submission):** An answer is accepted only if
  `server_accepted_at ≤ QuestionWindow.submission_close_at` for its
  `question_window_id`; late answers are rejected or recorded as TIMEOUT. (FR-20)
- **BR-10 (Second Chance):** Only one extra attempt (`attempt_no = 2`) is allowed
  after a WRONG first attempt; it is scored at `second_chance_rate`. (FR-24)
- **BR-11 (Fifty-Fifty timing):** Fifty-Fifty cannot be activated after an answer
  is selected and always preserves the correct option. (FR-23)
- **BR-12 (Skip scoring):** SKIP awards full correct points under Fixed scoring
  and the floor score under Speed. (FR-25)
- **BR-13 (Wildcard limits):** Activations respect the enabled set, per-type
  `usage_limit`, `eligibility`, `cooldown_questions`, and group
  `carry_over`/reset rules configured in `WildcardConfig`. (FR-26)
- **BR-14 (Tie-break order):** Ties are resolved by fastest total response time,
  then fewest wrong answers, then earliest `last_correct_at`; deterministic and
  logged. (FR-15)
- **BR-15 (Group rollup):** Contest score is computed by the contest's rollup
  strategy (`SUM` | `WEIGHTED_SUM` | `BEST_N`). (FR-16)
- **BR-16 (Elimination effect):** Once an EliminationEvent exists for a
  participant, their `Registration.status` becomes `ELIMINATED` and no further
  AnswerSubmissions are accepted. (FR-36)
- **BR-17 (Survivor carry-forward):** Survivors retain accumulated scores across
  groups unless a reset is configured for the next group. (FR-37)
- **BR-18 (Leaderboard/summary recoverability):** `LeaderboardEntry` and
  `ParticipantScoreSummary` are derived state; both can be rebuilt from
  authoritative `Score` rows on cache loss without affecting scores or ranks.
  (FR-44)
- **BR-19 (Tenant identity & email uniqueness):** `Organization.slug` and
  `portal_url` are unique platform-wide; `custom_domain`, if set, is also unique.
  `User.email` is unique within a tenant, and `SUPER_ADMIN` emails are unique
  platform-wide. (FR-1, FR-4)
- **BR-20 (Configuration scope invariant):** A ConfigurationBlock has exactly one
  of (`contest_id`, `group_id`). (FR-8)
- **BR-21 (Exactly one correct option):** Each Question has exactly one Option
  with `is_correct = true`. (FR-10)
- **BR-22 (Question window authority):** `QuestionWindow` holds the
  server-authoritative reveal, close, and evaluation times; client times are
  display-only. (FR-17, FR-20)
- **BR-23 (Resumable execution state):** `ContestExecutionState` is the single
  durable record the Execution Engine reads to resume a Live contest; on recovery
  it is reconciled only from durable rows (windows, submissions, scores), never
  from cache. (FR-42, NFR-6)
- **BR-24 (At-least-once outbox):** An `OutboxEvent` is written in the same
  transaction as its state change and marked `PROCESSED` only after the
  downstream consumer acknowledges; unprocessed events are re-driven on recovery,
  and idempotent consumers prevent double effects. (FR-38, FR-39)
- **BR-25 (Survivor score reset):** Survivors carry accumulated scores into the
  next group unless the group's `ConfigurationBlock.survivor_score_reset` is
  true. (FR-37)
- **BR-26 (Refresh-token rotation):** Refresh tokens belong to a token family;
  using a token revokes it (`revoked_at`) and issues a new token linked by
  `replaced_by`; reuse of a revoked token revokes the entire family. (FR-4)
- **BR-27 (Immutability / idempotency / result snapshot):** Duplicate
  submissions are rejected by `idempotency_hash`; once a Contest is `Archived`,
  its ConfigurationBlock, Questions, Options, AnswerSubmissions, and Scores are
  read-only; a `ContestResultSnapshot` is written once on Archive and never
  modified. (FR-39, FR-41, FR-45)
