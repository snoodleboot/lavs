# Contributing

Hi all, if you would like to contribute to this project, then the following are the ways we would like to see collaboration

1. Look at the official task board for the project (WIP) and take on one of the tasks.
2. If there is a feature you think is valuable, then create a PR draft and present the idea to the core team.
3. If you find a bug, please work a solution that aligns both with the coding style and design requirements for the project. Then create a PR.

Branch requirements

Name branches `{type}/{ticket}-{description}`:

1. `{type}` is one of:
   - `feat/` — a new feature
   - `bugfix/` — a bug fix that can wait for the next release
   - `hotfix/` — an urgent fix that needs to ship immediately
2. `{ticket}` is the issue the work tracks — a GitHub issue number (e.g. `63`), or a Linear key (e.g. `LAV-64`) for work tracked there. If there is no issue yet, open one before branching.
3. `{description}` is 3–5 words in kebab-case.

For example: `feat/63-e2e-ci-job`, `bugfix/54-migration-backend-portability`, `feat/LAV-64-dependency-editor`.

When the work is tracked in Linear, put the key in the PR title as well, so Linear links the PR to the issue.