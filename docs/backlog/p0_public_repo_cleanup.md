# P0 · Public repository cleanup

Status: in progress
Priority: P0 / High
Owner: project maintainer

## Scope

- Remove tracked local context files covered by `.gitignore`.
- Review current repository tree for internal-only project notes.
- Decide whether the repository remains public or becomes private.
- Keep public tree limited to code, tests, safe docs, examples, and env examples.
- Add a short cleanup checklist to project docs.

## Progress

- `.gitignore` now ignores local agent and private context files.
- Tracked `cotext.md` was removed from the repository.
- `context.md` and `CLAUDE.md` were checked and are not present in the current tree.
- GitHub open issue search for P0/blocker/critical items returned no open GitHub issues.

## Remaining acceptance criteria

- Confirm there are no other internal-only context files in the current tree.
- Decide and document public vs private repository mode.
- Move this backlog item into Jira/GitHub Issues when issue creation is available.

## Notes

GitHub and Jira issue creation was attempted from the agent session, but external issue creation was blocked by the connected tool. This repository backlog item preserves the task until it can be moved into Jira/GitHub Issues manually.
