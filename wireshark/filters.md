# Useful Wireshark display filters

Apply these after capturing. They are **display filters**, not tcpdump/capture-filter syntax. Ports below are the default project ports. Use actual configured ports and the stream number observed in your capture if they differ.

| Filter | Purpose |
|---|---|
| `dns` | DNS queries and responses, including decoded TCP DNS |
| `udp.port == 53` | UDP DNS traffic |
| `tcp.port == 53` | TCP DNS traffic |
| `dns.flags.response == 0` | DNS questions |
| `dns.flags.response == 1` | DNS responses |
| `dns.qry.name == "app.team1.test"` | Default app lookup; adapt if the team name changes |
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
| `tcp.port == 8443` | Default edge connection |
| `tcp.port == 3001 || tcp.port == 3002` | Default backend connections |
| `http` | Decoded plaintext backend HTTP; ordinary encrypted edge traffic will not match |
| `tcp.analysis.retransmission` | Actual retransmissions, if any were captured |

For an entire connection, right-click a relevant packet and choose **Follow → TCP Stream**, or enter `tcp.stream == N` using the actual stream number from that packet. A SYN-only filter hides the final ACK, so use the complete stream to demonstrate all three handshake packets. You can narrow any filter using the real addresses shown in the capture; do not substitute example addresses as evidence.

Expand TCP fields to read source/destination ports, sequence number, acknowledgement number and window. Application payload for HTTPS is encrypted in a normal packet capture; filtering it does not decrypt it. TLS 1.3 also encrypts the Certificate message, so use the additional validated TLS 1.2 capture described in [README.md](README.md) for the visible certificate requirement.
