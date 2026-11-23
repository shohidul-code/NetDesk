# Security matrix → tests

Every row of the security control matrix (PROPOSAL §10.2) and the automated test that
verifies it. CI runs all of them on every push. Paths are under `tests/`.

| Threat | Verification | Test(s) |
| --- | --- | --- |
| Password theft from a DB dump | Hash is `$argon2id$v=19$m=19456,t=2,p=1` | `test_seed.py` (seeded admin hash) |
| Brute force, credential stuffing | 6th login/min → 429; equal 401 bodies; dummy hash for unknown email | `test_rate_limit.py::test_sixth_login_from_one_ip_is_429_with_our_envelope`, `test_auth.py::test_unknown_email_and_wrong_password_get_identical_401`, `test_auth.py::test_unknown_email_still_runs_a_hash_check` |
| Forged or expired token | Tampered, expired and `alg=none` → 401 | `test_auth.py::test_token_signed_with_another_key_is_401`, `::test_expired_token_is_401`, `::test_unsigned_alg_none_token_is_401` |
| Stale privileges | Deactivated user's next call → 401; role change applies at once | `test_auth.py::test_deactivated_user_token_stops_working`, `::test_role_change_takes_effect_without_a_new_token` |
| Missing role check | Route walk; customer × every write route → 403 | `test_rubric_rules.py::test_every_non_public_route_requires_auth`, `::test_only_docs_and_the_guarded_mcp_route_live_outside_fastapi_auth`, `test_access_sweep.py::test_every_write_route_rejects_customer`, `::test_sweep_covers_the_write_routes` |
| Object-level access (IDOR) | Another customer's connection, bill, complaint, chat → 404 | `test_access_sweep.py::test_other_customers_connection_is_404`, `::test_other_customers_bill_is_404`, `::test_customer_cannot_complain_about_other_customers_connection`, `::test_idor_404_body_matches_a_missing_id`, `test_chat.py::test_another_users_session_is_404` |
| Cross-tenant access | Single tenant in the MVP | Not applicable (P2: row-level security) |
| SQL injection | `q=%' OR 1=1 --` returns 0 rows, no 500 | `test_connections.py::test_q_escapes_like_wildcards_and_sql` |
| Mass assignment | Register with `"role": "admin"` → 422 | `test_register.py::test_invalid_input_is_422_and_never_echoed`, `test_users.py::test_role_in_the_body_is_rejected` |
| Cost runaway, chat abuse | 31st message/day → 429; per-minute and global caps; kill switch | `test_chat.py::test_31st_message_of_the_day_is_429`, `::test_seventh_message_in_a_minute_is_429`, `::test_global_cap_is_429`, `::test_kill_switch_gives_503` |
| CORS abuse | Unknown origin gets no CORS headers | `test_cors.py::test_unknown_origin_gets_no_cors_headers` |
| Secret leakage | `repr(settings)` hides secrets; gitleaks in CI | `test_config.py::test_secrets_are_hidden_in_repr`, CI `security` job (gitleaks) |
| Sensitive logs | No password in a login's logs; phones, tokens, search text redacted; uvicorn logs go through the same formatter | `test_log_redaction.py` (all) |
| Error leakage | 500 has no traceback; 422 never echoes input | `test_rubric_rules.py::test_500_body_has_no_traceback`, `::test_422_body_never_echoes_input` |
| Vulnerable dependencies | CI fails on a known high-severity CVE | CI `security` job (pip-audit, npm audit); Dependabot |
| Malicious documents | Oversized, non-UTF-8 and HTML documents are rejected or stripped | `test_ingest.py::test_size_limit_is_50_kb`, `::test_non_utf8_is_rejected`, `::test_html_is_stripped`, `::test_front_matter_must_start_and_close` |
| Prompt injection | Injection eval cases: 0 successes; evidence fenced as data | `docs/EVAL_RESULTS.md` (0 successful injections), `test_eval_chat.py::test_injection_checks_text_and_tool_misuse`, `test_rag.py::test_evidence_block_is_labelled_as_data` |
| Unauthorized tool execution | A customer's model asking for a staff tool is refused | `test_agent_tools.py::test_tool_is_refused_exactly_when_role_not_allowed`, `::test_unknown_tool_is_refused_and_logged`, `test_chat.py::test_invented_staff_tool_call_is_refused` |
| MCP access | No token → 401; customer → 403; unknown host → 421; stdio needs active staff | `test_mcp_http.py` (all), `test_mcp_stdio.py::test_customer_email_is_refused`, `test_mcp_server.py::test_non_staff_callers_are_refused_inside_the_server` |
| Destructive actions | Delete a connection with bills → 409; last admin cannot be deactivated | `test_connections.py::test_delete_connection_with_bills_is_409`, `test_users.py::test_cannot_deactivate_the_last_active_admin` |
| Oversized requests | 1 MB body → 413 (declared or streamed, also `/mcp`) | `test_body_limit.py` (all) |
| Data sent to the LLM provider | Tool output has no phone or address, for every tool and role | `test_tool_privacy.py::test_tool_output_has_no_phone_or_address` |
