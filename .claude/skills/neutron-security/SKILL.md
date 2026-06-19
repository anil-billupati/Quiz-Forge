---
name: neutron-security
description: Apply when editing or reviewing code that involves
             authentication, authorisation, secrets handling, external
             input processing, API endpoints, data persistence of
             sensitive data, or infrastructure configuration. Read
             .neutron/security.md before acting.
model: sonnet
version: 1.0.0
---

# Neutron Security

## What this skill enforces
Fission's security baseline across all projects. Security is not a
final review step — it is applied at the point code is written.

## When this skill applies
When any of the following are being written or reviewed:
- Authentication or authorisation logic
- Secret, credential, token, or API key handling
- External input processing — HTTP requests, queue messages, file uploads
- Database queries involving user data
- API endpoint definitions and handlers
- Infrastructure configuration files
- Dependency additions or updates
- Logging code near sensitive data paths

## When this skill does not apply
- Pure UI components with no data handling
- Test utilities and fixtures (unless they handle real credentials)
- Documentation-only changes
- Refactoring with no logic change

## Rules

1. Read `.neutron/security.md` before acting on any security-relevant
   code. Understand the project's auth mechanism, compliance requirements,
   and sensitive data types before writing or reviewing anything.

2. No secrets in code, config files, or environment files. All secrets
   via environment variables referencing the project's secrets manager.
   If a secret appears in code, flag it immediately — do not proceed.

3. Validate all external inputs. Trust no input from outside the service
   boundary. Validation must happen at the entry point, not deeper in
   the call stack.

4. Authentication must be verified on every request to a protected
   endpoint. Do not rely on upstream services to have already
   authenticated.

5. No wildcard CORS. Allowed origins must be explicit and documented
   in `.neutron/security.md`.

6. Sensitive data must not appear in logs. Mask or omit PII, credentials,
   tokens, and payment data from all log output. Check `.neutron/security.md`
   for the project's list of sensitive data types.

7. Dependencies must be pinned to exact versions in production builds.
   New dependencies must be reviewed before addition:
   - Last release date
   - Open security advisories
   - License compatibility
   - Download volume as a proxy for community health

8. SQL queries must use parameterised queries or an ORM. No string
   concatenation in queries. No exceptions.

9. Any security-relevant decision — choosing an auth pattern, selecting
   a secrets strategy, handling a compliance requirement — triggers
   neutron-adr-capture for Tier 1 decisions or a decisions.md entry
   for Tier 2.

10. If a security concern is identified that cannot be addressed in the
    current change, it must be documented as a known issue before the
    change proceeds. It does not block the change but it must not be
    silently left.
