# Codexers — real Phase 1 evidence

**Infrastructure:** Type 2 — two physical macOS laptops with combined roles. The team reports that live LAN, DNS, HTTPS, balancing, caching, Wireshark and Backend A stop/recovery demonstrations were completed. The recorded LAN addresses were Laptop 1 `10.7.18.118` and Laptop 2 `10.7.31.46`.

This checkout currently contains this index and `.gitkeep` files only. The filenames below are **instructions for attaching your actual saved artifacts**, not claims that those files exist. Do not generate sample screenshots or terminal output as deployment evidence. Local automated tests are development checks, not physical deployment evidence.

## Evidence folders and filenames

| Folder | Real files to attach |
|---|---|
| `lan/` | `laptop1-ip.png` or `.txt`; `laptop2-ip.png` or `.txt`; `ping-laptop1-to-laptop2.png` or `.txt`; `ping-laptop2-to-laptop1.png` or `.txt` |
| `dns/` | `client-dig.txt` or screenshot; `public-dns-nxdomain.txt` or screenshot; optional reviewed `dnsmasq-config.txt`; macOS scoped-resolver verification if used |
| `backends/` | `backend-a-direct.txt`; `backend-b-direct.txt` |
| `nginx/` | `load-balancing.txt`; reviewed `nginx-relevant-config.txt` |
| `tls/` | `https-curl-v.txt`; optional `certificate-validation.png`; public SAN/validity/fingerprint observation |
| `caching/` | `cache-headers.txt`; `etag-304.txt` |
| `wireshark/` | `dns.png`; `tcp-handshake.png`; `tls-handshake.png`; actual reviewed `.pcap`/`.pcapng` files if requested |
| `failures/` | `before-backend-failure.txt`; `backend-a-down.txt`; `restored.txt` |

## What each artifact should show

- **LAN:** Both actual addresses and both ping directions; include interface/subnet/gateway/MAC inventory if collected.
- **DNS:** Private app/API answers of `10.7.31.46` from dnsmasq `10.7.18.118`, and public Google DNS NXDOMAIN for `app.codexers.test`. Label a direct dig query separately from macOS application resolution on the managed Mac.
- **Backends:** Direct A :3001 and B :3002 responses, matching JSON and `X-Backend` headers.
- **nginx:** A/B selections over `https://app.codexers.test:8443`, the relevant equal-weight upstream configuration and successful config check if saved.
- **TLS:** Successful HTTPS without a verification bypass and a matching app-domain SAN. Do not include private keys.
- **Caching:** `/cache-demo` gives `Cache-Control: public, max-age=60` and ETag; an actual matching `If-None-Match` request gives 304 without a body. `/api/status` is intentionally no-store.
- **Wireshark:** DNS query/response, TCP SYN/SYN-ACK/ACK, TLS handshake and encrypted application records, with packet/stream references. In the reported connection, A's source port was 59218; it is not permanent.
- **Failure:** The selected live Option A — stop Backend A, all requests served by B, restart A and A/B selection resumes. The other four reference scenarios are not claimed completed live.

## Save or copy genuine output

Prefer the already recorded outputs/screenshots. If repeating a healthy check on the actual deployed LAN, commands such as these save new genuine output:

```sh
./scripts/test_load_balancing.sh > evidence/nginx/load-balancing.txt 2>&1
./scripts/test_caching.sh > evidence/caching/etag-304.txt 2>&1
```

Run from the repository root and check each saved file for the actual result. Use reviewed text excerpts for logs, since generated `.log` files are ignored. Save distinct filenames for the two physical ping directions. For a new inventory, run `python3 scripts/_common.py inventory --laptop 1` on A or `--laptop 2` on B; use the real interface if not the default. Do not substitute this development machine's inventory for either deployment laptop.

Keep `network.env`, TLS keys, generated certificates, DNS backups and unrelated personal/network traffic out of Git. Review captures and config excerpts before making the repository public; safe evidence PNG/text files remain visible to Git. Preserve relevant technical fields and identify deliberate redactions. Evidence descriptions in this index do not manufacture missing files.

Use [Wireshark instructions](../wireshark/README.md), [the live failure account](../docs/FAILURE_ANALYSIS.md), and [the checklist](../docs/EVALUATION_CHECKLIST.md). Follow the root README's GitHub workflow to attach reviewed artifacts. The final video goes to Google Drive using the recording filename, duration/size limits and link access described in the README.
