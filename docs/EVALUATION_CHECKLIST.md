# Codexers — Phase 1 evaluation checklist

**Infrastructure:** Type 2 — 2 physical macOS laptops with combined roles, supported by the Phase 1 submission form.

Checked items record the team's reported successful live deployment. Six original screenshots are attached: bidirectional ping results, TCP and TLS Wireshark views, and one background TLS view. The remaining checked results are still team-reported, with no corresponding attachments in this checkout. [The evidence index](../evidence/README.md) lists the actual files and missing attachments; the background view is not project-handshake proof.

- [x] Two laptops connected to same LAN
- [x] Laptop 1 IP recorded: `10.7.18.118`
- [x] Laptop 2 IP recorded: `10.7.31.46`
- [x] Ping works Laptop 1 → Laptop 2
- [x] Ping works Laptop 2 → Laptop 1
- [x] dnsmasq running on Laptop 1
- [x] `app.codexers.test` resolves to `10.7.31.46`
- [x] `api.codexers.test` resolves to `10.7.31.46`
- [x] Public Google DNS returns NXDOMAIN for `app.codexers.test`
- [x] Backend A running on `10.7.18.118:3001`
- [x] Backend B running on `10.7.31.46:3002`
- [x] nginx running on Laptop 2
- [x] HTTPS works without `-k`
- [x] TLS certificate validation succeeds
- [x] subjectAltName matches `app.codexers.test`
- [x] `X-Backend: A` observed
- [x] `X-Backend: B` observed
- [x] Round-robin balancing demonstrated
- [x] Cache-Control demonstrated on `/cache-demo`
- [x] ETag demonstrated
- [x] `304 Not Modified` demonstrated
- [x] Wireshark DNS capture completed
- [x] Wireshark TCP handshake capture completed
- [x] Wireshark TLS handshake capture completed
- [x] Failure demo completed: Backend A stopped
- [x] Backend B continued serving requests
- [x] Backend A restored
- [x] A/B balancing resumed
- [ ] Final 5-minute video uploaded
- [ ] Google Form submitted

## Submission coverage

| Area | Recorded deployment / submission content |
|---|---|
| LAN | Two physical hosts, recorded IPs and bidirectional ping |
| Private DNS | Laptop 1 dnsmasq; app/API → Laptop 2; public NXDOMAIN comparison; managed-Mac scoped resolver where needed |
| Backends | A :3001 and B :3002, JSON and backend headers |
| Edge | Laptop 2 nginx, HTTPS :8443 and equal-weight round robin |
| TLS | Certificate validation and app-domain SAN; no validation bypass |
| Caching | `/cache-demo`, max-age=60, ETag, conditional 304; `/api/status` intentionally no-store |
| Wireshark | Real DNS, TCP SYN/SYN-ACK/ACK and TLS capture observations |
| Selected failure | **Option A — Stop Backend A**, B continues, restart A and balancing resumes |
| Deliverables | Architecture, configuration bundle, source, evidence index, final video and form |

The form requires one selected failure demonstration. The other scenarios retained in [FAILURE_ANALYSIS.md](FAILURE_ANALYSIS.md) are reference procedures and are not marked as completed live. Use [the recording plan](../README.md#5-minute-demo-recording), fill both enrollment numbers and the section label, attach real evidence, then upload the video and submit the form.
