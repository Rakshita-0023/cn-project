**Permission boundary:** this is an evaluation runbook, not an instruction to stop or change services during passive QA. Steps 8/9 and shutdown require an authorized demonstration window. The faculty challenge is pending.

# Final demonstration: all 11 steps from Section 8

Before evaluation complete the [fresh-start runbook](../../phase2/README.md),
`make test-local`, both live inventories and the isolation acceptance check.
Keep both Macs awake, both edges running, rollback terminals open and captures
ready. Rakshita and Lakshya should each explain the other person's services.
Use `source <(python3 phase2/network.py env)` in every demonstration shell.

| # | Required step | Execute / show | Owner and evidence |
|---|---|---|---|
| 1 | Topology and IP/service inventory | Open `docs/phase2/architecture.svg`; `make inventory`; `make status` | Both; actual JSON inventories and service map |
| 2 | Private LAN | `./scripts/test_ping.sh` on both Macs; show `ipconfig getifaddr "$LAN_INTERFACE"` | Both; bidirectional actual output |
| 3 | Resolve private domain | `dig @"$DNS_IP" "$APP_DOMAIN" A`; repeat with `DNS_BACKUP_IP`; `python3 phase2/network.py test dns` | Rakshita; show server IP, A answer and TTL |
| 4 | HTTPS using domain | `python3 phase2/network.py test https`; browser `https://app.codexers.test:8443` | Lakshya; no validation bypass or warnings |
| 5 | A/B load balancing | `python3 phase2/network.py test balancing` | Lakshya; show both `X-Backend` values |
| 6 | DNS/TCP/TLS packet evidence | Open `evidence/phase2/pcaps/dns-tcp-tls.pcapng`; DNS frames 16/17, TCP 18/19/20, TLS 21/24; explain TLS 1.3 encrypted Certificate | Both; actual packet numbers, ports and explanations |
| 7 | HTTP caching | `python3 phase2/network.py test caching`; show `Cache-Control`, ETag, empty 304 | Rakshita; separate HTTP freshness from DNS TTL |
| 8 | Fail one backend | On Mac 1: `make demo-backend`; show B-only responses and restored A/B | Rakshita stops/restores; Lakshya explains upstream logs |
| 9 | Phase 2 resilience | Perform A, B, C and E below, not just one of them | Both; live evidence for every mandatory extension |
| 10 | Faculty-injected fault | `make diagnose`; narrate first failed layer and independent later checks; use recovery guide | Both; save actual fault, hypothesis, repair, retest |
| 11 | Individual viva | Each answers questions in `VIVA.md` from understanding | Both; do not read answers during the viva |

## Step 9 expanded: all mandatory behaviors

**A - Backup DNS:** on Mac 1 stop only `dns-primary`, flush caches on both clients,
then on both run `python3 phase2/network.py test backup`. Show a packet/query log
to **Mac 2's DNS**, not just a cached successful HTTP request. Restart primary
and `test dns`. `make demo-dns` automates Mac 1's stop/check/restore window; use
manual service control when the peer needs longer to collect evidence.

**B - TTL:** warm native lookup, then update both resolvers as described in the
fresh-start guide. In another terminal run `observe --seconds 45`. Compare direct
new A answers with native cached old edge, then expiry. Repeat and flush before
expiry to demonstrate immediate update. Save the actual observed timestamps;
never substitute a predicted cache duration. `make ttl-lab` supplies repeatable
automated forwarding-cache evidence as a separate supporting experiment.

**C - Isolation:** show `firewall status` and run `test isolation` on **both**
ordinary client users. Demonstrate failed direct connections to A and B while
authenticated HTTPS through both edges still receives A/B responses. Show the
ready `make rollback` command and rollback record. An IP-only rule is insufficient
for clients sharing an edge host.

**E - Migration:** verify the standby edge first, keep both edges serving, then
run `records --target standby --ttl 30` on Mac 2 and Mac 1. Confirm both servers'
new A records and eventually native `X-Edge: edge-standby` using `test migration`.
Show cached old versus fresh new traffic, then run `make restore` on both and
retest. DNS TTL does not move an already-open TCP/TLS connection.

## Capture preparation

Use Wireshark on the real LAN interface **and loopback**. The following creates
real captures and requires an administrator; Ctrl+C stops each. Select unique
filenames to preserve earlier evidence. Run in separate terminals:

```sh
mkdir -p evidence/phase2/live
sudo tcpdump -i "$LAN_INTERFACE" -s 0 -U -w evidence/phase2/live/lan.pcap 'port 53 or tcp port 8443 or tcp port 3001 or tcp port 3002'
sudo tcpdump -i lo0 -s 0 -U -w evidence/phase2/live/loopback.pcap 'port 53 or tcp port 8443 or tcp port 3001 or tcp port 3002'
```

Adjust capture filter ports if configuration changed. For visible TLS 1.2
Certificate/ChangeCipherSpec packets, force a fresh validated connection:

```sh
curl --noproxy '*' --http1.1 --tlsv1.2 --tls-max 1.2 --cacert phase2/tls/ca.crt -v "https://$APP_DOMAIN:$HTTPS_PORT/api/status"
```

TLS 1.3 encrypts Certificate after ServerHello. Do not label unrelated background
TLS as project proof. In Wireshark use `dns`, `tcp.stream == N`,
`tls.handshake.type == 1`, `tls.handshake.type == 2`, `tls.handshake.type == 11`,
and backend ports. If 8443 is not decoded as TLS use Decode As. Record actual
stream/packet numbers, source ephemeral port, destination port, sequence, ACK
and advertised window. Save capture names in `TEST_RESULTS.md`.

At the end restore primary DNS targets on both Macs, then `make cleanup` on
both. Keep evidence and run `make bundle` after updating live test results.

Use [SUBMISSION_CHECKLIST.md](../../SUBMISSION_CHECKLIST.md) for missing reciprocal, current acceptance, Phase 1 failure, and packet evidence. Topic exports are in evidence/phase2/exports. The clean pcapng is preferred; the partial pcap is not a complete capture.
