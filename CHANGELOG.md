# Changelog

## v0.1.1 - 2026-04-27

- Added input sanitization, prompt-injection spotlighting, and system-prompt guardrails.
- Added daily token-budget tracking with SQLite persistence and router-level hard caps.
- Hardened PDF, DOCX, XLSX, Markdown, and text parsing before ingestion.
- Added chat input limits, budget status, reset controls, safer admin authentication, and localhost admin binding.
- Added operator runbook and regression tests for security-sensitive behavior.
