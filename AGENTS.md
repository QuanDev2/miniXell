# miniXell Agent Rules

This repo is a learn-by-building project. The user is learning the stack
(Python, PySpark, Scala, MongoDB, FastAPI, AWS) while building it. Teaching is
part of the job, not optional.

## Teaching loop: every phase and every step

1. **Brief before building.** Before starting any phase or step, teach what
   the user needs to understand it:
   - concise and high level first;
   - the purpose of each piece;
   - how the pieces work together.
2. **Wait for questions.** The user drives depth with follow-up questions.
   Answer at the depth asked; don't front-load detail.
3. **Wait for an explicit go** before building.
4. **Build only that step.**
5. **Recap** what was built and why, briefly.

## Step-by-step execution: no hands-off runs

- Execute one step at a time, then **stop**.
- After each step, the user reviews and may commit before allowing the next
  step.
- Never continue to the next step without the user's explicit go, even when
  the next step is obvious or was approved as part of a larger plan.
- Approving a list of steps is not approval to run them back to back.
- Run steps hands-off only if the user explicitly says so, and only for the
  steps they name.

## MVP first

- This is an MVP for an interview demo: speed over perfection.
- Prefer the quickest correct option. For non-blocking imperfections, state
  the impact in one line and recommend accepting; don't hold up progress.
- Only stop for issues that would make results wrong or block the next phase.

## Progress log

- [docs/PROGRESS.md](docs/PROGRESS.md) is the handoff log. Read it first to
  find the current phase, step, and what's next.
- Update it after every step: status, commit hash (or "uncommitted"), the
  next step, and any decision or environment change not already in
  PLAN/ARCHITECTURE.

## References

- Plan and phases: [docs/PLAN.md](docs/PLAN.md)
- Progress and next step: [docs/PROGRESS.md](docs/PROGRESS.md)
- Architecture and schema: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Science and math explained: [docs/CONCEPTS.md](docs/CONCEPTS.md)
- Company research: [docs/COMPANY_RESEARCH.md](docs/COMPANY_RESEARCH.md)
