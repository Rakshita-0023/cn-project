# Phase 1 evaluation checklist

These boxes represent the future physical deployment. Local loopback tests do not mark physical evidence complete. Both members should be able to explain every part.

- [ ] Both laptops on same LAN
- [ ] IP addresses recorded, with interface, subnet/mask, gateway and MAC addresses
- [ ] Ping works both ways
- [ ] DNS working on Laptop 1 over UDP and TCP
- [ ] `app.team1.test` resolves to Laptop 2
- [ ] `api.team1.test` resolves to Laptop 2
- [ ] Both real clients use the private DNS resolver
- [ ] Backend A running on Laptop 1, port 3001
- [ ] Backend B running on Laptop 2, port 3002
- [ ] nginx running on Laptop 2 after successful configuration validation
- [ ] HTTPS works for both names on the configured HTTPS port
- [ ] Certificate trusted on both Macs; both SANs and validity checked
- [ ] `X-Backend: A` observed
- [ ] `X-Backend: B` observed
- [ ] Round-robin requests and response headers explained
- [ ] Caching demonstrated: `Cache-Control`, ETag, conditional 304 with no body
- [ ] DNS Wireshark evidence: question, answer, resolver, addresses and ports
- [ ] TCP handshake evidence: SYN, SYN-ACK, ACK and socket ports
- [ ] TCP sequence/acknowledgement numbers and receive window explained
- [ ] TLS handshake evidence: ClientHello, ServerHello, certificate-related packets, encrypted traffic
- [ ] Additional TLS 1.2 capture identifies Certificate and ChangeCipherSpec
- [ ] All five failure demonstrations completed and restored
- [ ] Evidence saved and reviewed for accidental private data
- [ ] Configuration bundle and complete source ready for submission
- [ ] Both members prepared for individual Phase 1 viva
- [ ] Faculty confirmation recorded for the literal DNS client-count limitation

If the team label or ports are deliberately changed in `network.env`, evaluate the actual configured names/ports and record them. The normal example is team1 with backend ports 3001/3002 and HTTPS 8443.

## Assignment coverage

| Area | Implementation / demonstration |
|---|---|
| Task A: LAN setup | Two actual inventories, shared LAN, ping in both directions |
| Task B: Private DNS | dnsmasq on Laptop 1, both names map to Laptop 2, real client resolver settings; literal client count needs faculty confirmation |
| Task C: Backend services | A and B direct responses and identification headers |
| Task D: Edge and balancing | Laptop 2 nginx, equal-weight pool, forwarded headers, both selections |
| Task E: TLS / HTTPS | SAN certificate, trusted clients, validated HTTPS and handshake |
| Task F: Caching / transport | max-age, validators, 304, TCP sequence/ACK/window explanation |
| Task G: Packet evidence | Actual DNS, TCP, TLS and encrypted HTTPS captures |
| Failures | All five procedures in [FAILURE_ANALYSIS.md](FAILURE_ANALYSIS.md) |
| Deliverables / viva | Architecture, configuration bundle, source, genuine evidence and individual explanation |

The original assignment's Phase 1 scope is Tasks A–G in §6.2, all five failures in §6.3, and the relevant deliverables in §9. Review 1 in §10 is 50 marks: LAN/DNS 10, backends/edge 10, TLS 8, packet evidence 7, caching/transport 5, and individual viva 10. Providing the files does not complete the live evaluation or guarantee marks.

The team uses two physical Macs and combines machine roles. The assignment's specific requirement asking two other Macs to use the DNS resolver cannot be literally demonstrated with two physical Macs and should be confirmed with faculty. An unchecked faculty-confirmation box is not a claim of approval. Capturing loopback traffic does not create another physical Mac.
