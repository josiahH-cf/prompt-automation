Goals

Keep files small and cohesive (target ≤ 300–400 LOC per file; ≤ 75 LOC per function unless clearly justified).

Reuse existing logic before writing new logic.

Prefer extraction to new modules over appending to large files.

Before writing code

Search @workspace for existing functions/classes/utilities that satisfy the request; list candidates with file paths and signatures.

If a target file would exceed the size/complexity thresholds, propose an Extract-Function/Extract-Module refactor with:

New filename and destination folder

Public API (exports) and minimal new logic

A list of import updates for callers

When refactoring

Create the new file, move only the necessary logic, keep public signatures stable, and update imports across the workspace.

Keep modules single-purpose and name files by capability (e.g., parseInvoice.ts not utils2.ts).

If the refactor is too large or complex, break it into smaller steps and document each step's purpose.

Quality

Follow existing lint/format rules; prefer simple, composable functions.

If similar logic exists, unify by calling the existing function or delegating to it rather than duplicating.

Document the change: short summary of moved symbols and affected files.