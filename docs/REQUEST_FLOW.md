# A Phase 1 request, end to end

```text
DNS lookup at Laptop 1
  → TCP connection to Laptop 2's HTTPS port
  → TLS handshake and certificate validation
  → encrypted HTTPS request to Laptop 2 nginx
  → nginx selects Backend A or Backend B
  → separate HTTP request to that backend
  → backend response through nginx
  → encrypted response to the client
```

1. The client asks Laptop 1's dnsmasq for `APP_DOMAIN` or `API_DOMAIN`. A records return Laptop 2's `EDGE_IP`. DNS replies give an address; DNS does not relay the later web request. Cached answers may avoid a new DNS query.
2. The client opens TCP to `EDGE_IP:HTTPS_PORT`. The new connection begins with SYN, SYN-ACK and ACK. The client's ephemeral source port differs from the server's configured destination port.
3. TLS negotiates cryptographic parameters. The client checks the certificate's trust anchor, validity, and SAN matching the requested domain. SNI tells nginx which hostname the client requested. The public certificate alone is not the private key.
4. The client sends HTTP inside TLS. Packet capture shows encrypted application data; curl and the browser can display HTTP after their own TLS processing.
5. nginx terminates TLS and chooses an equal-weight upstream by round robin. It sends HTTP to Laptop 1 Backend A on `BACKEND_A_PORT` or Laptop 2 Backend B on `BACKEND_B_PORT`, forwarding the host and client/protocol headers. This is a separate TCP connection from the client's connection.
6. The backend responds with JSON and `X-Backend: A` or `B`. nginx returns that response to the client through TLS. `X-Backend` identifies the responder even though the browser connects to one edge address.

Both clients are co-located with server roles. Laptop 1's query to its own DNS and Laptop 2's requests to its own edge/backend can appear on local interfaces. Capture the actual LAN interface and loopback; see [Wireshark instructions](../wireshark/README.md).

## Cache path

`/api/status` uses `Cache-Control: no-store`, keeping the load-balancing demonstration visible. `/cache-demo` and its retained `/api/cache` alias send `Cache-Control: public, max-age=60` and an ETag. Both backends intentionally share this representation and ETag.

A browser may reuse fresh cached content without a network request. A conditional request sends `If-None-Match` with the actual ETag; an unchanged representation produces `304 Not Modified` with no response body. nginx forwards this behavior without introducing its own proxy cache. Repeating ordinary curl commands does not by itself demonstrate persistent browser caching.

## Failed path

Use the furthest successful step to locate the problem. Wrong resolver: no usable name lookup. Wrong record or port: connection goes to a wrong endpoint. Untrusted certificate: TCP succeeds but TLS validation fails. Both backends stopped: DNS, TCP and TLS can succeed before nginx returns HTTP 502. The [five failure demonstrations](FAILURE_ANALYSIS.md) make these distinctions observable.
