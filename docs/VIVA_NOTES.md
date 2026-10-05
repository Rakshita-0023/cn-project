# Phase 1 viva notes

Both Person A and Person B should explain the full system, including components running on the other laptop.

| Topic | Concise answer |
|---|---|
| DNS | Maps the private app/API names to Laptop 2. Laptop 1 answers the lookup; it does not forward web requests. |
| TCP | Connection-oriented transport with ordered delivery, acknowledgements, retransmission and flow control. |
| UDP | Datagram transport without TCP's connection/reliability mechanisms. DNS commonly queries over UDP and also supports TCP. |
| Ports | Distinguish service endpoints on a host. Here DNS is 53, A is 3001, B is 3002, HTTPS defaults to 8443. |
| TCP handshake | SYN → SYN-ACK → ACK establishes the connection and synchronizes sequence numbers. |
| Sequence / ACK / window | Track byte positions, the next expected byte, and how much unacknowledged data the receiver permits. |
| TLS | Authenticates the server and establishes encryption/integrity above TCP. Here it terminates at nginx. |
| HTTPS | HTTP exchanged over TLS; application payload is encrypted in a normal packet capture. |
| Certificate | Binds a public key to identity. Check SAN hostname, validity period and trusted anchor; keep the private key secret. |
| SAN / SNI / ALPN | SAN lists certificate names; SNI communicates the requested server name; ALPN negotiates application protocol. |
| Reverse proxy | nginx receives client requests and makes separate requests to backends, hiding their selection behind one edge endpoint. |
| Load balancing | Distributes requests across A and B. `X-Backend` and nginx logs reveal the selected server. |
| Round robin | Equal-weight healthy upstreams are selected in rotation. Other clients and temporarily failed upstreams affect a visible sequence. |
| Cache-Control | `public, max-age=60` permits caching this representation for 60 seconds; status uses `no-store`. |
| ETag | Identifies the current representation. Both backends share identical cache content and therefore the same tag. |
| 304 | A matching `If-None-Match` means the representation has not changed; send headers without the body. |
| Wireshark | Captures/decodes actual packets. Capture LAN plus loopback because client/server roles share two hosts. |
| DNS vs application failure | A DNS error prevents finding the edge; a 502 can occur after correct DNS and successful TCP/TLS when upstreams fail. |
| 200 / 304 / 502 | Successful representation / unchanged cached representation / edge cannot obtain an upstream response. |
| TLS 1.2 vs 1.3 | TLS 1.2 permits a visible certificate handshake demonstration; TLS 1.3 encrypts Certificate after ServerHello. |
| HTTP versions | HTTP/1.1 works here; optional HTTP/2 multiplexes streams; HTTP/3 uses QUIC over UDP and is not implemented. |
| Cloud / CDN comparison | DNS resembles managed DNS, nginx resembles an edge/load balancer, and backends resemble application instances. A CDN can cache content geographically; this project does not deploy one. |
| SMTP / IMAP / POP3 | SMTP sends mail; IMAP accesses/synchronizes server mailboxes; POP3 retrieves mail. Explain these course protocols without deploying mail services. |

## Diagnose in order

```sh
python3 scripts/_common.py diagnose
```

This read-only helper checks DNS, system resolution, TCP, TLS and HTTP. Its explicit query to the private server is distinct from the client's configured resolver. Use actual output to identify the first failed step.

| Symptom | Check | Corrective action |
|---|---|---|
| Peer ping fails | Actual addresses/interface, subnet, shared LAN, peer isolation | Correct config/LAN reachability; record both real directions |
| Direct DNS times out | Laptop 1 dnsmasq, port 53 and its runtime log | Start project DNS and resolve a conflicting listener |
| Direct DNS works, system lookup fails | `scutil --dns`, network-service settings, DNS caches, VPN/secure DNS | Set project client DNS and flush caches |
| DNS returns Laptop 1 | Rendered record and running dnsmasq | Render normal config, restart DNS, flush clients |
| TCP edge connection fails | Destination IP/port and nginx listener | Start nginx on Laptop 2 after config validation |
| TLS validation fails | SAN, anchor, expiry, Mac clock | Trust correct public certificate and use the configured hostname |
| Only one backend appears | Direct backend tests and nginx logs | Restart failed backend; allow passive failure expiry |
| HTTP 502 | Both backend processes and direct reachability | Restore backends and retest |
| Cache always returns 200 | Actual endpoint/tag and quoted If-None-Match | Use `test_caching.sh` to send the real ETag |
| Capture lacks packets | Capture interfaces, DNS cache, fresh connection, TLS version | Capture LAN/loopback and fresh validated requests |

Rehearse explaining why stopping Backend A preserves DNS, but switching off Laptop 1 removes both services. Neither laptop is a redundant edge or DNS server. Describe only the failures and recovery you actually observed.

The team uses two physical Macs and combines machine roles. The assignment's specific requirement asking two other Macs to use the DNS resolver cannot be literally demonstrated with two physical Macs and should be confirmed with faculty.

## Primary references

The assignment remains the source of required behavior. These sources support the technical explanations:

- [dnsmasq manual](https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html)
- [nginx upstream](https://nginx.org/en/docs/http/ngx_http_upstream_module.html), [proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html), and [SSL](https://nginx.org/en/docs/http/ngx_http_ssl_module.html) modules
- [HTTP caching, RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html)
- [TLS 1.3, RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html)
- [TCP, RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html)
