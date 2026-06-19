---
name: neutron-documentation
description: Apply when a function, method, class, module, or API
             endpoint is being created or meaningfully changed.
             Write documentation as part of the same step as the code.
             Documentation written after the fact is documentation
             that does not get written.
model: haiku
version: 1.0.0
---

# Neutron Documentation

## What this skill enforces
That documentation is produced alongside code, not after it. The
standard for documentation quality is that a competent engineer
unfamiliar with this codebase can understand what a function does,
why it exists, and how to use it without reading its implementation.

## When this skill applies
When any of the following are being produced or changed:
- New public functions, methods, or classes
- Modified public function or method signatures
- New or modified API endpoints
- New modules or significant new files
- Complex logic that is not self-evident from the code

## When this skill does not apply
- Private helper functions where the name and context make purpose
  clear — docstrings are still encouraged but not enforced
- Test functions — test names serve as documentation
- Generated or scaffolded boilerplate
- Trivial one-line functions where the implementation is the
  clearest documentation

## Rules

1. Every public function, method, and class has a docstring or JSDoc
   comment. One sentence minimum stating what it does.
   Not what the code does line by line — what the unit's purpose is.

2. Docstring format follows the convention for the project's language:
   - Python: Google-style docstrings (Args, Returns, Raises, Example)
   - TypeScript/JavaScript: JSDoc (param, returns, throws, example)
   - Java: Javadoc (param, return, throws, since)

3. Complex or non-obvious logic has an inline comment explaining why,
   not what. The code explains what. The comment explains why this
   approach was taken.

4. API endpoints have:
   - Description of what the endpoint does
   - All parameters documented with type and description
   - Response schema documented
   - At least one example request and response
   - Error responses documented

5. New modules and significant new files have a module-level docstring
   or header comment explaining:
   - What this module/file is responsible for
   - What it is not responsible for (scope boundary)
   - Any important usage notes

6. Documentation is updated when code changes. Stale documentation
   is worse than no documentation. If changing a function's behaviour,
   update its docstring in the same commit.

7. README is updated if:
   - Setup steps change
   - A new environment variable is required
   - The way to run tests changes
   - A significant new capability is added
