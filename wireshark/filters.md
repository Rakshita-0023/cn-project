# Codexers — useful Wireshark display filters

Apply these to the actual saved captures. They are **display filters**, not tcpdump/capture-filter syntax. The recorded client was `10.7.18.118` and nginx was `10.7.31.46:8443`. Addresses may change on another LAN. Use the stream number observed in your capture.

| Filter | Purpose |
|---|---|
| `dns` | DNS queries and responses, including decoded TCP DNS |
| `udp.port == 53` | UDP DNS traffic |
| `tcp.port == 53` | TCP DNS traffic |
| `dns.flags.response == 0` | DNS questions |
| `dns.flags.response == 1` | DNS responses |
| `dns.qry.name == "app.codexers.test"` | Codexers app lookup |
| `tcp` | All TCP |
| `tcp.flags.syn == 1 && tcp.flags.ack == 0` | Initial SYN |
| `tcp.flags.syn == 1 && tcp.flags.ack == 1` | SYN-ACK |
| `tcp.flags.ack == 1 && tcp.flags.syn == 0` | ACK-bearing packets, including data; locate the handshake's third packet within its stream |
| `tls` | Decoded TLS records |
| `tls.handshake` | Visible decoded TLS handshake messages |
| `tls.handshake.type == 1` | ClientHello |
| `tls.handshake.type == 2` | ServerHello |
| `tls.handshake.type == 11` | Visible Certificate, typically the fresh TLS 1.2 demo |
| `tls.record.content_type == 20` | ChangeCipherSpec record |
| `tls.record.content_type == 23` | Application-data records; TLS 1.3 also uses this outer type for encrypted handshake content |
| `tcp.port == 8443` | Recorded HTTPS edge connection |
| `tcp.port == 3001 || tcp.port == 3002` | Default backend connections |
| `http` | Decoded plaintext backend HTTP; ordinary encrypted edge traffic will not match |
| `tcp.analysis.retransmission` | Actual retransmissions, if any were captured |

For the recorded TLS traffic between the two physical Macs:

```text
tls && tcp.port == 8443 &&
ip.addr == 10.7.18.118 &&
ip.addr == 10.7.31.46
```

The reported TCP handshake used source port 59218 on Laptop 1 and destination port 8443 on Laptop 2. `tcp.port == 59218 && tcp.port == 8443` can isolate that recorded connection's packets, but 59218 is an ephemeral source port and must not be assumed for later captures.

For an entire connection, right-click a relevant packet and choose **Follow → TCP Stream**, or enter `tcp.stream == N` using the actual stream number from that packet. A SYN-only filter hides the final ACK, so use the complete stream to demonstrate all three handshake packets. You can narrow any filter using the real addresses shown in the capture; do not substitute example addresses as evidence.

Expand TCP fields to read source/destination ports, sequence number, acknowledgement number and window. Application payload for HTTPS is encrypted in a normal packet capture; filtering it does not decrypt it. TLS 1.3 also encrypts the Certificate message, so use the additional validated TLS 1.2 capture described in [README.md](README.md) for the visible certificate requirement.
