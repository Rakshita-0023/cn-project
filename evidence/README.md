# Codexers — real Phase 1 evidence

**Infrastructure:** Type 2 — two physical macOS laptops with combined roles. Laptop 1 / Person A used `10.7.18.118` for DNS, Backend A :3001 and client testing. Laptop 2 / Person B used `10.7.31.46` for nginx / HTTPS :8443, Backend B :3002 and client testing.

This index describes the **six original screenshots actually attached to this repository**. They were inspected and moved into folders without changing their contents. Local test output is not included as physical deployment evidence.

## Attached files and what they show

| File | Visible evidence |
|---|---|
| [lan/ping-laptop1-to-laptop2.png](lan/ping-laptop1-to-laptop2.png) | Person A's terminal runs `ping -c 4 10.7.31.46`: four replies, four received and `0.0% packet loss`. The direction is identified from Person A's terminal identity and the known Laptop 2 destination; the source IP is not printed in this screenshot. |
| [lan/ping-laptop2-to-laptop1.png](lan/ping-laptop2-to-laptop1.png) | Person B's terminal shows `10.7.31.46`, followed by `ping -c 4 10.7.18.118`: four replies, four received and `0.0% packet loss`. |
| [wireshark/tcp-handshake.png](wireshark/tcp-handshake.png) | The `tcp.port == 8443` view shows SYN → SYN-ACK → ACK between `10.7.18.118:59218` and `10.7.31.46:8443`, followed by a TLS ClientHello with SNI `app.codexers.test` and encrypted traffic. |
| [wireshark/tls-handshake.png](wireshark/tls-handshake.png) | The endpoint-specific TLS filter shows TLS 1.3 ClientHello/ServerHello and application records, plus a separate TLS 1.2 handshake with Certificate, Server Key Exchange, Change Cipher Spec and encrypted records. This is the primary TLS screenshot. |
| [wireshark/tls-handshake-serverhello-selected.png](wireshark/tls-handshake-serverhello-selected.png) | An additional view of the same endpoint-specific filter, with a TLS 1.3 ServerHello row highlighted and the TLS 1.2 certificate/key-exchange sequence also visible. Preserved as supporting evidence. |
| [wireshark/tls-background-traffic.png](wireshark/tls-background-traffic.png) | A broad `tls` filter shows Laptop 1 exchanging encrypted application records with public Internet addresses. The selected packet uses source port 443, not the project edge port 8443. This is background-traffic context, **not proof of the project's TLS handshake**. |

Port **59218 is the ephemeral source port of that captured connection**, not a permanent project port. HTTP application payload remains encrypted in the client-to-nginx TLS capture. These Wireshark views do not prove macOS certificate trust, a successful `curl` verification, backend selection or caching headers.

## Original filenames

All six input images are preserved byte for byte; no screenshots or terminal results were generated during organization.

| Original filename in `evidence/` | Current location |
|---|---|
| `Screenshot 2026-10-05 at 2.09.02 PM.png` | `lan/ping-laptop1-to-laptop2.png` |
| `evidence_ping_mac2_to_mac1.png` | `lan/ping-laptop2-to-laptop1.png` |
| `evidence_wireshark_tcp_handshake.png` | `wireshark/tcp-handshake.png` |
| `Screenshot 2026-10-05 at 4.27.00 PM.png` | `wireshark/tls-handshake.png` |
| `evidence_wireshark_tls_clean.png` | `wireshark/tls-handshake-serverhello-selected.png` |
| `evidence_wireshark_tls_noisy.png` | `wireshark/tls-background-traffic.png` |

## Evidence still to attach

The [evaluation checklist](../docs/EVALUATION_CHECKLIST.md) records the team's reported live results. The following attachments are absent from this checkout; their absence does not establish that a reported live test failed.

| Folder | Missing real attachments |
|---|---|
| `lan/` | Dedicated IP/interface/subnet/gateway/MAC inventory. The existing images show ping results and captured addresses, not complete interface inventory. |
| `dns/` | dnsmasq configuration, private app/API answers from `10.7.18.118`, public-DNS NXDOMAIN comparison and managed-Mac resolver verification if recorded. |
| `backends/` | Direct responses from A :3001 and B :3002 with matching `X-Backend` headers. |
| `nginx/` | The upstream/configuration and the repeated request loop showing both A and B. |
| `tls/` | Terminal HTTPS success without a certificate-verification bypass, SAN match and certificate validation/trust evidence. Wireshark images belong in `wireshark/`. |
| `caching/` | `/cache-demo` headers (`Cache-Control: public, max-age=60`, ETag, Date, X-Backend) and a matching conditional request returning `304 Not Modified`. `/api/status` intentionally uses `no-store`. |
| `wireshark/` | DNS query/response screenshot and original packet-capture files if faculty expects them. TCP and project TLS screenshots are already attached. |
| `failures/` | The selected **Option A — Stop Backend A** sequence: A/B before, B only while A is stopped, then A/B after A restarts. Other failure scenarios are not claimed demonstrated live. |

The six otherwise empty category directories are retained with `.gitkeep`. Copy only real, reviewed files into them and update this index when those files are attached. Do not substitute development tests or sample output for recorded deployment evidence.

Keep `network.env`, private keys, generated certificates, runtime logs/PIDs, saved DNS settings and credentials out of Git. The attached screenshots include terminal identities, LAN/MAC addresses and, in the background view, public server addresses; they are preserved as supplied. Review any additional screenshots and packet captures before publishing them.

See [the Wireshark guide](../wireshark/README.md), [the live failure account](../docs/FAILURE_ANALYSIS.md), and [the recording plan](../README.md#5-minute-demo-recording). Enrollment numbers, the section label, the final video upload and the form submission remain separate submission tasks.
