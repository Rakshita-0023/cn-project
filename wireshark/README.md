# Codexers — Phase 1 Wireshark observations and capture guide

The team reports completing DNS, TCP and TLS captures during the recorded Type 2 deployment. Attached [TCP](../evidence/wireshark/tcp-handshake.png) and [TLS](../evidence/wireshark/tls-handshake.png) screenshots show the real client/edge addresses and handshake details below. [The evidence index](../evidence/README.md) also preserves an additional filtered TLS view and a broad background-traffic view. A DNS screenshot and original packet-capture files are not attached in this checkout.

## Recorded connection details

| Role | Recorded address |
|---|---|
| Laptop 1, main HTTPS client and DNS server | `10.7.18.118` |
| Laptop 2, nginx edge and secondary DNS client | `10.7.31.46` |
| HTTPS destination | TCP 8443 |
| Private name | `app.codexers.test` → `10.7.31.46` |

The team-reported DNS exchange was **Laptop 2 client → Laptop 1 DNS server**, using UDP destination port 53. The reported reply mapped `app.codexers.test` to `10.7.31.46` with TTL 30. This DNS exchange is separate from the main client's HTTPS connection and is not visible in the attached TCP/TLS screenshots.

The observed client-to-edge TCP handshake was:

```text
10.7.18.118:59218 → 10.7.31.46:8443  SYN
10.7.31.46:8443 → 10.7.18.118:59218  SYN-ACK
10.7.18.118:59218 → 10.7.31.46:8443  ACK
```

**59218 was the ephemeral source port in that captured connection.** A new client connection can use a different port; no source-port setting is added to the project.

For the TLS stream, identify **ClientHello**, **ServerHello**, **Certificate**, **Server Key Exchange**, **Change Cipher Spec**, and **Encrypted/Application Data** where visible for the negotiated version. Certificate, Server Key Exchange and Change Cipher Spec labels describe a full TLS 1.2 ECDHE handshake; TLS 1.3 has different visibility, explained below. Use the actual packet labels/version rather than asserting unseen messages. HTTP payload is not readable after TLS encryption begins in a normal capture.

A useful display filter for the recorded encrypted edge traffic is:

```text
tls && tcp.port == 8443 &&
ip.addr == 10.7.18.118 &&
ip.addr == 10.7.31.46
```

See [filters.md](filters.md) for DNS, SYN/SYN-ACK/ACK, TLS and backend filters.

## Repeat the capture if needed

Keep the completed deployment running, or follow the root [deployment guide](../README.md) to reproduce it. The instructions below create genuine new captures when executed on the real laptops; they do not supply pre-recorded evidence. Recorded IPs can change on another LAN, so load the current runtime variables.

## What each member captures

- **Person A / Laptop 1:** Main client requests to Laptop 2's nginx. Capture its DNS lookup, a new client-to-edge TCP handshake, TLS handshake, and encrypted HTTPS. A's lookup to its own resolver may be local; HTTPS to B crosses the LAN.
- **Person B / Laptop 2:** Client DNS queries to Laptop 1 and the edge's backend connections. Its own client-to-nginx connection and nginx-to-Backend B connection can be local. nginx-to-Backend A crosses the LAN.

Capture your actual Wi-Fi/LAN device **and `lo0`**, or use macOS `pktap,all` as below. A LAN-only trace can omit required packets when roles share computers. Loopback capture does not represent another physical Mac.

## Start a capture

On each laptop, load the validated variables in the capture terminal:

```sh
source <(python3 scripts/_common.py shell-env)
```

Open Wireshark and choose the actual active LAN interface and loopback together. Find the device with `networksetup -listallhardwareports` if needed. An optional **capture filter** is:

```text
port 53 or tcp port 8443 or tcp port 3001 or tcp port 3002
```

Those ports are the normal defaults; replace ports if your actual configuration differs. Do not confuse capture-filter syntax with [display filters](filters.md). Capturing without a filter is also valid if you review unrelated traffic before submission.

Alternatively capture all relevant Mac interfaces in Terminal. On Laptop 1:

```sh
sudo tcpdump -i pktap,all -nn -s 0 -w evidence/wireshark/laptop1-flow.pcap \
  "port 53 or tcp port $HTTPS_PORT or tcp port $BACKEND_A_PORT or tcp port $BACKEND_B_PORT"
```

On Laptop 2, use the same command with `evidence/wireshark/laptop2-flow.pcap`. These are capture commands, not ready-made evidence. Stop with Ctrl+C before opening the resulting file in Wireshark. If this capture device is unavailable, select the real LAN interface and `lo0` in Wireshark, or capture them separately with distinct filenames.

## Generate genuine traffic

In another terminal on each laptop:

```sh
source <(python3 scripts/_common.py shell-env)
TLS_ANCHOR=tls/certs/server.crt
if [ -f tls/certs/ca.crt ]; then TLS_ANCHOR=tls/certs/ca.crt; fi
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
curl --noproxy '*' --http1.1 --cacert "$TLS_ANCHOR" -v \
  "https://$APP_DOMAIN:$HTTPS_PORT/api/status"
./scripts/test_load_balancing.sh
./scripts/test_caching.sh
```

A new curl process creates a fresh connection. If no DNS packet appears, inspect the actual client resolver path and caches. A separate explicit `dig @"$DNS_IP" "$APP_DOMAIN" A` is useful, but identify it as a separate DNS query rather than claiming it belongs to curl's lookup. `dig +tcp @"$DNS_IP" "$APP_DOMAIN" A` demonstrates TCP DNS separately.

## Show certificate-related handshake packets

In TLS 1.3 the Certificate message is normally encrypted after ServerHello. You can see ClientHello, ServerHello and encrypted handshake records, but cannot read the certificate message in an ordinary capture. A compatibility ChangeCipherSpec record is not the TLS 1.3 key-change mechanism.

If your saved TLS 1.3 trace does not expose certificate-related messages needed for explanation, make an additional fresh **validated TLS 1.2** request while capturing. nginx keeps both TLS 1.2 and 1.3 enabled:

```sh
curl --noproxy '*' --http1.1 --tlsv1.2 --tls-max 1.2 --cacert "$TLS_ANCHOR" -v \
  "https://$APP_DOMAIN:$HTTPS_PORT/api/status"
```

Save this capture with a descriptive `tls12` filename. Identify ClientHello, ServerHello, Certificate, key-exchange-related messages, ChangeCipherSpec and encrypted Finished/application records. A fresh TLS 1.2 handshake makes Certificate visible; application content still stays encrypted. Neither command disables certificate verification.

## Annotate these observations

| Required observation | What to identify in actual packets |
|---|---|
| DNS query and response | Requested name/type, matching transaction ID, Laptop 1 resolver, Laptop 2 A-record answer, client source port and server port 53 |
| TCP SYN | Client ephemeral source port → configured edge destination port; SYN set |
| TCP SYN-ACK | Edge → client, SYN and ACK set; matching connection |
| TCP ACK | Final acknowledgement in the same stream; follow the stream so the ACK is not excluded by a SYN-only filter |
| TLS ClientHello | Requested SNI name, offered versions and cryptographic parameters |
| TLS ServerHello | Selected version and parameters |
| Certificate-related handshake | Actual TLS 1.2 Certificate/SAN observation; explain TLS 1.3 encrypted handshake visibility |
| HTTPS encrypted traffic | TLS application-data records rather than readable HTTP payload |
| Source/destination ports | Actual client ephemeral port, edge HTTPS port, and separate backend ports |
| TCP reliability / flow control | Real sequence/ACK fields and receive window; record retransmissions only if actually present |

Select a relevant packet, note its `tcp.stream` number, and filter that stream. If port 8443 is not recognized automatically, use **Analyze → Decode As → TLS** for the edge connection. Backend ports may need **Decode As → HTTP**.

nginx terminates TLS. Its separate backend HTTP can show readable headers and `X-Backend`; client-side HTTPS payload remains encrypted. The [request flow](../docs/REQUEST_FLOW.md) explains the boundary. Optional HTTP/2 should only be claimed if enabled and actually negotiated.

The attached [TCP handshake](../evidence/wireshark/tcp-handshake.png), [primary TLS view](../evidence/wireshark/tls-handshake.png) and [additional TLS view](../evidence/wireshark/tls-handshake-serverhello-selected.png) are indexed in [evidence/README.md](../evidence/README.md). The [background TLS view](../evidence/wireshark/tls-background-traffic.png) shows unrelated Internet traffic and is not project-handshake proof. Add the actual saved DNS screenshot and reviewed original captures if required; update the index with their real filenames and packet/stream references. Put the selected Backend A stop-and-restore evidence under `evidence/failures/`. Never present sample output as a live capture.

Technical references: [Wireshark User's Guide](https://www.wireshark.org/docs/wsug_html_chunked/), [TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html), and [TLS 1.2](https://www.rfc-editor.org/rfc/rfc5246.html).
