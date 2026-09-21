# Pull request review setup

## Current repository baseline

At the time this file was created, the repository has no application source code, dependency manifest, test suite, Docker configuration, CI/CD, environment-variable configuration, or authentication system. Consequently, there are no language-specific lint, test, type-check, build, container, or dependency checks to run yet.

The `Repository policy` workflow is deliberately minimal and deterministic: it confirms that the review guidance and pull-request template remain present. Add project checks to that workflow when a concrete stack is introduced; do not mark an empty or no-op check as evidence that application code was tested.

## How review works

1. A developer opens, updates, or reopens a pull request.
2. GitHub Actions runs the **Review foundation** check and verifies the review policy files.
3. The pull-request template asks the author to document behavioral changes, validation, tests, and risk.
4. Codex Code Review reads the applicable `AGENTS.md` instructions and examines the diff and relevant context for supported P0–P3 correctness, regression, reliability, and security issues.
5. When enabled in Codex settings, Codex can review eligible pull requests automatically. Otherwise, comment `@codex review` on the pull request.
6. For a deeper security pass, use `@codex security review` or configure Codex Security Review to run with Code Review.
7. A human reviewer evaluates findings, required checks, and the author’s validation before merging. Codex approval must not merge a pull request automatically.

Codex Code Review and Security Review are configured through Codex/GitHub integration settings rather than this workflow. This avoids storing an OpenAI API key or creating a duplicate, unsupervised review action in the repository. See the [official OpenAI guide](https://developers.openai.com/es-419/docs/third-party/github).

## Adding application checks

When code is added, update `.github/workflows/repository-policy.yml` in the same pull request with the project’s existing deterministic commands:

- package install plus lint, tests, type check, and build for application projects;
- migrations and integration tests only where their services are available;
- Docker build validation only when a Dockerfile exists;
- security/dependency scanning appropriate to the chosen ecosystem.

Pin third-party actions to immutable commit SHAs where your organization’s policy requires it, and keep credentials in GitHub Actions secrets or OIDC—never repository files.

## Manual GitHub settings

Configure these in the GitHub repository after merging this setup:

1. Connect the repository to Codex Cloud, then enable **Code Review** and, if desired, automatic PR reviews. Enable **Security Review** for the desired PR scope; it is an additional security pass.
2. Protect `main`: require pull requests before merging, require at least one human approval, dismiss stale approvals on new commits, require the **Review foundation** status check, require branches to be up to date before merging, and block force pushes and branch deletion.
3. Enable GitHub secret scanning and push protection. Enable Dependabot alerts and updates once dependency manifests exist.
4. Restrict GitHub Actions to approved actions and use least-privilege `GITHUB_TOKEN` permissions. Review any workflow that requests write permissions.
5. Add stack-specific required status checks only after they exist and are reliable. Do not require checks that cannot run for every protected-branch pull request.
