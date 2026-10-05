# Phase 1 protocol layers

| Layer | Meaning in this project | What to observe |
|---|---|---|
| Physical / link (OSI 1–2) | Wi-Fi/LAN carries frames; network interfaces have MAC addresses | Same reachable LAN, actual interface and MAC inventory; local traffic may use loopback |
| Network (OSI 3) | IP addresses identify the laptops and route packets | Source/destination IP, subnet/mask, default gateway; ping uses ICMP |
| Transport (OSI 4) | TCP or UDP ports identify services and socket endpoints | DNS UDP/TCP 53; edge HTTPS 8443 by default; backend TCP 3001/3002 |
| Session / presentation concepts (OSI 5–6) | TLS establishes an authenticated encrypted channel above TCP | Handshake, certificate validation, negotiated version and encrypted records |
| Application (OSI 7) | DNS, HTTP, reverse proxy and caching semantics | DNS answers, HTTP methods/status/headers, backend identity, cache validator |

The practical TCP/IP model groups these into link, internet, transport and application layers. TLS does not fit a single OSI label perfectly: it runs above TCP and protects application traffic. Explain its position and function rather than claiming it is TCP itself.

## Addresses and ports

An IP address identifies a host interface, a MAC address identifies a link interface, and a transport port identifies a service endpoint. A TCP connection is distinguished by source IP/port and destination IP/port. The client normally chooses an ephemeral source port; use the actual value from the capture. Changing the URL port changes the destination service even when DNS is correct.

DNS commonly uses UDP 53 for a question/answer exchange and also supports TCP 53. The project's DNS test checks both. A client-side UDP source port is normally ephemeral. HTTPS in this project uses TCP, while the DNS lookup remains a separate exchange.

## TCP reliability and flow control

SYN, SYN-ACK and ACK establish a connection and synchronize sequence numbers. Sequence numbers track bytes; acknowledgement numbers identify the next byte expected. A receiver advertises a window to limit outstanding data. TCP retransmits data when loss is detected, but a clean local test might not show retransmission. Explain the fields in a real stream and do not invent packet loss.

TCP establishes separate connections for client-to-nginx and nginx-to-backend. A failed backend connection need not break the already established client TLS connection. nginx can return an HTTP error through that healthy connection.

## Encryption boundary

TLS protects client-to-nginx HTTP. Backend HTTP is plaintext on this Phase 1 LAN, including the remote nginx-to-Backend A hop. A backend capture can therefore show HTTP headers that a client-side HTTPS capture cannot. TLS 1.3 encrypts most handshake messages after ServerHello, including Certificate. A separate fresh, validated TLS 1.2 request supports the assignment's visible Certificate and ChangeCipherSpec demonstration.

The configured HTTPS port is 8443 by default; port 443 is not required for HTTPS encryption to work. Record the actual port and explain its role. HTTP/1.1 is implemented; optional HTTP/2 negotiation depends on the installed edge/client support. HTTP/3 uses QUIC over UDP and is explanation-only here.
