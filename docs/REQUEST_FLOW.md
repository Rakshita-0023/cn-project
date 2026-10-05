# A Codexers Phase 1 request, end to end

Recorded Type 2 deployment: Laptop 1 DNS and Backend A at `10.7.18.118`, Laptop 2 nginx and Backend B at `10.7.31.46`. Both `app.codexers.test` and `api.codexers.test` resolve to Laptop 2, with HTTPS port 8443. These LAN addresses can change; runtime rendering still reads `network.env`.

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

**HTTP caching is demonstrated on `/cache-demo`.** Inspect the real deployed endpoint:

```sh
curl -sI https://app.codexers.test:8443/cache-demo
./scripts/test_caching.sh
```

Expected headers include `Cache-Control: public, max-age=60`, the actual quoted ETag, `X-Backend: A` or `B`, and `Date`. Use installed certificate trust, or supply the public anchor with `--cacert` if needed; do not bypass validation.

`/api/status` uses `Cache-Control: no-store`, keeping the load-balancing demonstration visible. `/cache-demo` and its retained `/api/cache` alias send `Cache-Control: public, max-age=60` and an ETag. Both backends intentionally share this representation and ETag.

A browser may reuse fresh cached content without a network request. A conditional request sends `If-None-Match` with the actual ETag; an unchanged representation produces `304 Not Modified` with no response body. nginx forwards this behavior without introducing its own proxy cache. Repeating ordinary curl commands does not by itself demonstrate persistent browser caching.

## Failed path

Use the furthest successful step to locate the problem. Wrong resolver: no usable name lookup. Wrong record or port: connection goes to a wrong endpoint. Untrusted certificate: TCP succeeds but TLS validation fails. Both backends stopped: DNS, TCP and TLS can succeed before nginx returns HTTP 502. These are reference explanations in [FAILURE_ANALYSIS.md](FAILURE_ANALYSIS.md).

**Live submission demo used Option A — Stop Backend A.** The team observed that DNS, TCP/TLS to the edge, nginx and Backend B continued working, then A/B balancing resumed after Backend A was restarted. The other scenarios are not claimed completed live.
