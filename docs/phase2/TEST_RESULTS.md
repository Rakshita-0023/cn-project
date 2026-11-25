# Phase 2 test results

Observed: 2026-11-25T16:20:18.171542+05:30

**Executed locally: 38/38 passed; 0 failures; 0 errors; 0 skipped.**

Scope: one accessible Mac, real loopback processes and ephemeral ports. Mock safety tests are identified by their test names. No live DNS settings, Keychain trust or PF rules were installed by the test suite.

Actual command: `make test-local`. [Complete text output](../../evidence/phase2/local-tests.txt), [per-case JSON](../../evidence/phase2/local-tests.json), [original baseline](../../evidence/phase2/phase1-baseline.txt).

| Test case | Actual result | Seconds |
|---|---|---|
| `test_local.BackendTests.test_cache_is_consistent_across_backends_and_supports_conditional_get` | PASS | 0.526 |
| `test_local.BackendTests.test_head_has_representation_headers_and_no_body` | PASS | 1.006 |
| `test_local.BackendTests.test_required_endpoints_identify_each_instance` | PASS | 1.022 |
| `test_local.ClientDNSStateTests.test_automatic_dns_restores_with_empty_and_failed_restore_keeps_backup` | PASS | 0.014 |
| `test_local.ClientDNSStateTests.test_preserves_manual_ipv4_ipv6_settings_across_repeated_changes` | PASS | 0.005 |
| `test_local.ClientDNSStateTests.test_stop_refuses_an_unrelated_pid` | PASS | 0.002 |
| `test_local.ConfigurationTests.test_alias_mismatch_is_rejected` | PASS | 0.001 |
| `test_local.ConfigurationTests.test_domain_injection_and_non_test_domain_are_rejected` | PASS | 0.003 |
| `test_local.ConfigurationTests.test_duplicates_unknown_keys_shell_expressions_and_ports_are_rejected` | PASS | 0.004 |
| `test_local.ConfigurationTests.test_example_environment_parses_and_aliases_match` | PASS | 0.000 |
| `test_local.ConfigurationTests.test_loopback_is_rejected_for_physical_deployment` | PASS | 0.001 |
| `test_local.ConfigurationTests.test_missing_runtime_environment_is_rejected` | PASS | 0.000 |
| `test_local.ConfigurationTests.test_quoted_values_comments_and_upstream_dns` | PASS | 0.001 |
| `test_local.EntrypointTests.test_direct_entries_and_shell_launchers_use_environment_and_clean_pid` | PASS | 2.166 |
| `test_local.EntrypointTests.test_optional_ca_chain_sans_permissions_and_no_silent_rotation` | PASS | 0.843 |
| `test_local.EntrypointTests.test_real_project_nginx_start_reload_stop_lifecycle` | PASS | 0.246 |
| `test_local.EntrypointTests.test_rendering_commands_and_start_reject_invalid_nginx` | PASS | 1.125 |
| `test_local.NetworkIntegrationTests.test_real_dnsmasq_answers_both_names_with_ttl_over_udp_and_tcp` | PASS | 0.194 |
| `test_local.NetworkIntegrationTests.test_real_nginx_tls_round_robin_caching_and_failures` | PASS | 7.516 |
| `phase2.tests.test_phase2.DNSIntegrationTests.test_both_resolvers_answer_identically_udp_tcp_and_primary_stop` | PASS | 1.404 |
| `phase2.tests.test_phase2.DNSIntegrationTests.test_real_forwarding_client_falls_back_after_primary_stops` | PASS | 1.536 |
| `phase2.tests.test_phase2.DNSIntegrationTests.test_real_ttl_expiry_record_change_and_cache_flush` | PASS | 4.152 |
| `phase2.tests.test_phase2.EdgeIntegrationTests.test_two_real_edges_tls_failover_recovery_and_caching` | PASS | 4.812 |
| `phase2.tests.test_phase2.SafetyTests.test_cleanup_continues_without_config_and_after_rollback_error` | PASS | 0.001 |
| `phase2.tests.test_phase2.SafetyTests.test_cli_rejects_invalid_counts_and_runs_from_other_directory` | PASS | 0.209 |
| `phase2.tests.test_phase2.SafetyTests.test_config_defaults_and_rejects_unsafe_values` | PASS | 0.002 |
| `phase2.tests.test_phase2.SafetyTests.test_diagnostics_continue_to_http_after_dns_and_tcp_fail` | PASS | 0.002 |
| `phase2.tests.test_phase2.SafetyTests.test_failed_record_publication_restores_original_record_state` | PASS | 0.001 |
| `phase2.tests.test_phase2.SafetyTests.test_failure_demo_restores_backend_even_when_the_probe_fails` | PASS | 0.000 |
| `phase2.tests.test_phase2.SafetyTests.test_firewall_apply_refuses_missing_anchor_without_loading_root_rules` | PASS | 0.000 |
| `phase2.tests.test_phase2.SafetyTests.test_firewall_refuses_loopback_skip_and_rolls_back_own_anchor_only` | PASS | 0.001 |
| `phase2.tests.test_phase2.SafetyTests.test_pid_reuse_and_remote_role_are_rejected` | PASS | 0.000 |
| `phase2.tests.test_phase2.SafetyTests.test_real_pf_syntax_check_without_loading_rules` | PASS | 0.009 |
| `phase2.tests.test_phase2.SafetyTests.test_record_state_and_config_snapshots` | PASS | 0.002 |
| `phase2.tests.test_phase2.SafetyTests.test_two_resolvers_are_passed_to_existing_backup_mechanism` | PASS | 0.001 |
| `phase2.tests.test_phase2.ServiceIntegrationTests.test_listener_inspection_rejects_wrong_socket_pid_and_inspection_errors` | PASS | 0.001 |
| `phase2.tests.test_phase2.ServiceIntegrationTests.test_missing_backend_listener_still_times_out_without_network_probe` | PASS | 0.000 |
| `phase2.tests.test_phase2.ServiceIntegrationTests.test_real_backend_start_conflict_restart_and_owned_stop` | PASS | 0.544 |

The standalone `make ttl-lab` writes independent TTL/flush output. Initial failed timing assumptions and intermediate debugging logs are retained in [the evidence index](../../evidence/phase2/README.md). They are not counted as passing results.

<!-- LIVE RESULTS -->







## Latest safe acceptance: FAIL (24 November 2026, 16:56:37)

Exact complete run: evidence/phase2/runs/20261124-165637-991096-test.txt.
Primary DNS answered; backup DNS timed out; native HTTPS resolution and pinned
primary-edge HTTPS timed out. No system settings or services were changed.
The complete run is not replaced by earlier separately passing checks.
See ../../SUBMISSION_CHECKLIST.md for remaining work and peer collection.

## Historical reviewed live results - 24 November 2026

See [the final report](FINAL_REPORT.md), Sections 3-7, for timestamps and exact evidence filenames.

| Area | Audited result |
|---|---|
| DNS backup failover | PASS from Rakshita during primary outage at earlier IP; native resolver 3.373s, HTTPS A/B |
| TTL and migration | Live primary-to-standby transition and rollback PASS at earlier IP; exact native cache lifetime not established |
| Isolation | PASS from Rakshita after reapply at 16:21 on 10.7.12.26; separate peer-client transcript absent |
| Backend HA | Live A-stop/B-only/recovery PASS at earlier IP |
| TLS, balancing, HTTP caching | PASS, including application checks after IP recovery |
| IP recovery / PF rollback | Owned-listener readiness PASS, scoped token rollback PASS, services restarted; intermediate aggregate test-all FAIL retained |
| Wireshark | Clean 72-packet pcapng verifies DNS/TCP/TLS; larger pcap has a truncated final packet |
| Faculty-injected fault | PENDING; toolkit/deployment troubleshooting do not substitute for faculty evaluation |

Current addresses: Rakshita 10.7.12.26; Lakshya 10.7.7.242. A new-IP full test-all PASS and repeat standby-target cutover are not separately saved. See report for peer inventory, reciprocal-client and packet-evidence gaps.
