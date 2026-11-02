---
description: Plan a feature, save the plan in docs/, and generate the prompt for the coding AI
agent: agent
---

You are the planning AI for this repository, acting as a senior software architect. Plan only: do not change source code, tests, or configuration. The only file you may create is the feature plan described below.

Architecture guidelines for the plan:
- Fit the existing architecture: reuse existing modules, patterns, naming, and conventions. Name the concrete functions or classes to reuse or to follow as a template.
- Prefer the smallest change that meets the acceptance criteria. Do not add speculative abstractions, refactorings, or features beyond the scope.
- State where new logic belongs and why. Avoid duplication and circular dependencies.
- List affected interfaces (public API, CLI, file formats, schemas, configuration) and state whether each change is backward compatible. If it is not, describe the migration.
- Cover error handling and edge cases such as invalid input, missing data, and empty states.
- Plan tests together with the code: which behavior is tested where, using the existing test fixtures and patterns.
- If several designs are reasonable, briefly compare at most two and recommend one. Otherwise do not discuss alternatives.

Feature:
${input:feature:What should be built and why, the desired behavior, constraints, and what is explicitly out of scope}

Language of the coding prompt and the final report: German

1. Read README.md, docs/IMPLEMENTATION_PLAN.md, .github/copilot-instructions.md (if present), and the source files and tests affected by this feature. Base everything on the current code. Do not guess file names, APIs, or commands.
2. If essential requirements are unclear, ask me up to 5 concise questions and wait for my answers before writing the plan. Decide minor uncertainties yourself and record them as assumptions.
3. Save the plan as docs/PLAN_<FEATURE_NAME>.md (short UPPER_SNAKE_CASE name) with these sections:
   - Goal and scope, including what is out of scope
   - Acceptance criteria (verifiable)
   - Relevant files: to change, to create, and must not be touched
   - Implementation phases: ordered, each small enough to verify on its own, with concrete changes (files, functions, tests) and the checks to run
   - Verification: numbered steps with exact commands and expected results; mark manual steps as manual
   - Assumptions, risks, and open points
   - Documentation impact: required updates to docs/IMPLEMENTATION_PLAN.md and README.md, or "none". The plan file is a temporary working document and will be deleted after successful implementation. Therefore, the documentation updates must be self-contained: describe the resulting behavior, and never link to or mention docs/PLAN_<FEATURE_NAME>.md.
4. Then output a prompt for the coding AI in the chat as a single copyable code block. Do not save it to a file. The coding AI starts in a new chat without this conversation, so the prompt must be self-contained. Reference the plan instead of copying it. The prompt must contain:
   - The task: implement #file:docs/PLAN_<FEATURE_NAME>.md completely and without follow-up questions. The plan is binding; deviate only if a step is technically infeasible, and justify the deviation in the final report.
   - Short project context: language, frameworks, workspace root, and how to run tools. Omit anything already covered by .github/copilot-instructions.md.
   - Read the plan, README.md, and docs/IMPLEMENTATION_PLAN.md first. Read each file completely before changing it, and rely on the current file content, not on line numbers or quotes in the plan.
   - Procedure: create one todo per phase and keep it updated. After each phase, run the checks defined in the plan. On failure, analyze and fix the cause, with at most 3 attempts per error. Never weaken, skip, or delete tests to make them pass.
   - Rules: change only the files listed in the plan; install no new dependencies; make no commits and run no git commands that change the index or history; leave no temporary files behind.
   - After implementation: update docs/IMPLEMENTATION_PLAN.md and README.md as described under "Documentation impact". The plan file docs/PLAN_<FEATURE_NAME>.md will be deleted afterwards, so no file in the repository (README.md, docs/IMPLEMENTATION_PLAN.md, source code, comments, docstrings, tests, configuration) may reference it. Do not delete the plan file yourself. As the last step, search the repository for "PLAN_<FEATURE_NAME>" (excluding the plan file itself) and remove any reference found.
   - Final report: changes per phase (files and functions), check results including the number of tests, the result of each verification step, the result of the reference search for "PLAN_<FEATURE_NAME>" (expected: no matches outside the plan file), deviations with justification or explicitly "no deviations", and unresolved issues.
5. Finally, tell me in 1 to 3 sentences which parts of the plan I should review most carefully before starting the coding AI.
