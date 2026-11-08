# Evaluation run 20261108T114838Z-live (live)

- Model: claude-haiku-5-5, max_tokens 300, temperature None (null = not sent, model default)
- Dataset sha256: e7512a65595ced4ba6ef3be4b09b112fefaff8ae4c385f967ab6bed38613c4ef
- Schema 1.0.0, prompt v1
- Pass rate: 2/2 (100.0%); guardrails 0/4; infra_error 24; input_error 0; fallbacks 0; not_run 0
- Estimated cost: $0.000000

Verdict: **FAIL**
- guardrail cases passed 0/4 (100% required)
- 24 infra_error cases (at most 2 allowed)

## Failing cases (paste into the coding agent)

- N-01 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- N-02 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- N-03 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- N-04 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- N-05 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- B-01 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- B-02 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- B-03 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- B-04 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- A-01 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- A-02 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- A-03 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- A-04 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- M-01 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- T-01 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- T-02 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- X-02 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- R-01 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- R-02 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- R-03 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- G-01 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- G-02 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- G-03 infra_error auth: authentication failed: AuthenticationError (HTTP 401)
- G-04 infra_error auth: authentication failed: AuthenticationError (HTTP 401)

SC-006: no measured cases
