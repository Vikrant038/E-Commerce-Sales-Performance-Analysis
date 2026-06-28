# CLAUDE.md — Engineering Guide & Governing Standards

> This file is the contract any human or AI follows when working in this repo.
> It binds the codebase to the **Enterprise Coding Standards**
> (`../../Enterprise-Coding-Standards/CODING_STANDARDS.md` + `GUARDRAILS.md`).
> `GUARDRAILS.md` wins on any security/reliability conflict.

## Project
An interactive **E-Commerce Sales Performance dashboard** (Streamlit) over a
cleaned star schema, with an optional multi-provider AI assistant. Read-only;
no user accounts, no writes, no real customer PII (public-style dataset).

## Risk tier (per GUARDRAILS.md)
**Internal Tooling / public demo.** Enforced pillars: **0** (global prohibitions),
**1** (naming), **2** (architecture/sizing/errors), **5** (docs), **6** (git),
**7** (testing), plus security **1.4** (secrets), **2.1** (input validation),
**2.6** (safe errors), **Module 3** (edge cases / timeouts), **6.4** (log redaction).

**Not applicable** (and why): CSRF/JWT/RBAC/sessions, REST versioning & idempotency,
DB migrations, SSRF, OAuth, React/frontend pillars — there is no auth layer, no
write API, no database, no user-supplied URLs, and no React. Outbound calls go
only to a fixed, configured LLM provider endpoint.

## Conventions adopted (Python mapping of the standards)
- **Naming (Pillar 1):** `snake_case` functions/vars, `PascalCase` classes,
  `SCREAMING_SNAKE_CASE` module constants. No single-letter vars except loop
  `i/j/k`, `x/y`, catch `exc`. No generic names (`data`, `tmp`, `res`, …).
- **Architecture (Pillar 2):** logic lives in `src/` modules; `streamlit_app.py`
  only wires widgets to those functions. Functions ≤30 lines / files ≤200 lines,
  or carry an `@size-exception` note in the documented format.
- **Errors (Pillar 0.2 / 2.6):** no empty `except`; provider failures raise
  `LLMError` with a user-safe message — never a stack trace or secret.
- **Logging (Pillar 0.3 / 6.4):** use the `logging` module, never `print`; never
  log API keys.
- **Secrets (GUARDRAILS 1.4):** read from `st.secrets`/env only; `.env` and
  `.streamlit/secrets.toml` are gitignored; `.env.example` documents the keys.
- **Edge cases (Module 3):** empty-filter → friendly empty state; AI question
  length-capped; request timeout + per-session AI call cap; AI never sees PII or
  runs code.
- **Testing (Pillar 7):** `pytest` in `tests/`, run in CI on every push.
- **Git (Pillar 6):** Conventional Commits; never commit secrets or `.venv`.

## Commands
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run streamlit_app.py     # run the app
pytest -q                          # run the tests
python -m src.clean                # rebuild Gold from Bronze -> datasets/_rebuilt/
```

## AI assistant
Provider-agnostic (`src/llm.py`): drop in an `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
or `GEMINI_API_KEY` and it's used automatically (override with `LLM_PROVIDER` /
`LLM_MODEL`). See `.env.example`. With no key, the AI tab degrades to a notice and
the rest of the app works.

## Map
`src/` modules (see `src/README.md`) · `scripts/` SQL pipeline · `tests/` pytest ·
`docs/` case study + video script · `.github/workflows/ci.yml` CI.
