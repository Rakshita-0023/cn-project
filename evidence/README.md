# Genuine Phase 1 evidence

This repository initially contains only this index and empty tracked directories. Capture evidence after both physical Macs are deployed. Automated local tests are development checks, not evidence of the two-laptop deployment. There are no pre-recorded results or fabricated screenshots.

Run from the repository root. Save screenshots as PNG/PDF, safe terminal output as `.txt`, and actual packet captures as `.pcap`/`.pcapng`. Use descriptive filenames with the laptop and demonstration, and include enough context to identify the real command, result, addresses and capture interface. Generated `.log` files are ignored; export reviewed excerpts as `.txt` if submitting them.

| Folder | What to save after deployment |
|---|---|
| `lan/` | Laptop 1 and Laptop 2 IP screenshots, interface/subnet/gateway/MAC inventory, ping 1→2 and ping 2→1 |
| `dns/` | Both clients' project DNS settings, dig for app/API with Laptop 1 as SERVER and Laptop 2 as answer, optional nslookup, UDP/TCP query checks |
| `backends/` | Backend A and B direct responses, `/api/status`, listening ports, actual `X-Backend: A/B` headers |
| `nginx/` | Successful config validation, actual edge A/B response headers, sequential load-balancing output, relevant sanitized access/error excerpts |
| `tls/` | Successful validated HTTPS, browser without trust warning, public certificate SANs/validity/fingerprint, client trust evidence |
| `caching/` | `Cache-Control: public, max-age=60`, initial 200/ETag, matching conditional request and 304 without body; optional browser cache observation |
| `wireshark/` | Real DNS exchange, TCP handshake, TLS handshake, encrypted HTTPS traffic, ports and packet/stream references; include fresh TLS 1.2 certificate/ChangeCipherSpec evidence |
| `failures/` | Each of the five injected faults, observed output, layer explanation and successful restoration; include one-backend survival and both-backend 502 |

The retained inventory command writes actual machine data only when you run it:

```sh
# On Laptop 1
python3 scripts/_common.py inventory --laptop 1
```

```sh
# On Laptop 2
python3 scripts/_common.py inventory --laptop 2
```

If Wi-Fi is not `en0`, add `--interface` with the actual device found using `networksetup -listallhardwareports`.

For example, after real deployment you can record a live check with:

```sh
./scripts/test_backends.sh > evidence/backends/direct-checks.txt 2>&1
./scripts/test_dns.sh > evidence/dns/query-checks.txt 2>&1
./scripts/test_load_balancing.sh > evidence/nginx/load-balancing.txt 2>&1
./scripts/test_caching.sh > evidence/caching/conditional-cache.txt 2>&1
```

Read each saved output and confirm success; the filenames alone do not establish that a check passed. Run ping on both physical laptops and save distinct direction/laptop filenames. Copy the other member's evidence into the appropriate directory through your normal team workflow.

Keep private keys, runtime configs, `network.env`, DNS backups and unrelated personal/network traffic out of Git. Captures can contain LAN addresses, hostnames and plaintext backend traffic; review them before sharing. Preserve the technical fields faculty needs, and identify any deliberate redaction. Record faculty confirmation separately if obtained; do not imply it already exists.

Use [Wireshark instructions](../wireshark/README.md), [failure procedures](../docs/FAILURE_ANALYSIS.md), and [the evaluation checklist](../docs/EVALUATION_CHECKLIST.md) when collecting. After reviewing genuine evidence, add and push it using the root README's GitHub workflow.
