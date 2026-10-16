# Security Policy

## Reporting a vulnerability

Do **not** open a public issue for security problems, credentials, or suspected secrets exposure.

Use **"Report a vulnerability"** (private vulnerability reporting) in this repository's **Security** tab. If that option is unavailable, contact the repository owner directly through a private channel.

Include: affected version/commit, impact, reproduction steps, and any suggested mitigation. Do not include live credentials or tokens in the report.

## Handling

- Reports are acknowledged and triaged privately.
- Suspected leaked secrets are treated as exposed regardless of history rewriting; rotate at the source system first.
- Fixes are coordinated with the reporter before public disclosure where feasible.

## Baseline

This repository follows the Zenastra Repo Security Baseline (standards/REPO_SECURITY_BASELINE.md in dev-slax/knowledge): Dependabot alerts and security updates enabled, dependency updates on a minimal cadence, and CI security checks (secret scanning, dependency audit, static analysis) on private repositories.
