# Codexers — Phase 1 failure analysis

## Live submission demo — Option A

**Live submission demo used Option A — Stop Backend A.** The submission form requires one selected failure demonstration. The team completed this scenario on its two physical Macs:

| Stage | Reported live result |
|---|---|
| Before | Laptop 2 nginx alternated between Backend A (`10.7.18.118:3001`) and Backend B (`10.7.31.46:3002`) |
| Action | Backend A process on Laptop 1 was stopped with Ctrl+C |
| After | All successful requests showed `X-Backend: B` |
| Affected layer | Backend/application service layer; nginx's connection to A could no longer reach that process |
| Still working | DNS, client-to-nginx TCP, TLS, nginx edge and Backend B |
| Restore | Restart Backend A with `python3 backend/backend_a.py` on Laptop 1 |
| After restore | A/B round-robin balancing resumed after the passive failure window |

The client continued using `https://app.codexers.test:8443/api/status` with certificate verification enabled. Save the actual before/down/restored output under `evidence/failures/`; this account does not assert those files are already attached.

## Reversible procedures

The five procedures below are retained for troubleshooting and course discussion. **Only the Backend A stop scenario was reported demonstrated live.** Wrong client DNS, wrong record, both backends stopped and wrong port are reference scenarios, not additional completed submission demonstrations.

Complete the healthy two-laptop deployment first. Inject one fault at a time, save the real result and restoration result in `evidence/failures/`, and restore before continuing. Leave DNS, nginx, and unaffected backends running. Commands start at the repository root. In every client terminal:

```sh
source <(python3 scripts/_common.py shell-env)
TLS_ANCHOR=tls/certs/server.crt
if [ -f tls/certs/ca.crt ]; then TLS_ANCHOR=tls/certs/ca.crt; fi
```

After either DNS fault and its restoration, run on both clients:

```sh
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

Use fresh curl processes. Browser secure DNS, VPN resolvers, or cached answers can mask the fault; inspect `scutil --dns` and the actual packet capture. Never use an IP URL or a validation bypass to conceal a DNS/TLS failure.

## 1. Wrong DNS server configured on the client — reference

**HOW TO BREAK:** On Laptop 2 confirm it has no DNS service on port 53 using `sudo lsof -nP -iUDP:53 -iTCP:53`. Then change only Laptop 2's client resolver to its own actual address:

```sh
./dns/set_client_dns.sh --server "$LAPTOP2_IP"
if [ -f "/etc/resolver/$TEAM_NAME.test" ]; then
  printf 'nameserver %s\nport 53\n' "$LAPTOP2_IP" | sudo tee "/etc/resolver/$TEAM_NAME.test"
fi
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
dig +time=2 +tries=1 "$APP_DOMAIN" A
curl --noproxy '*' --cacert "$TLS_ANCHOR" --connect-timeout 4 --max-time 10 \
  -v "https://$APP_DOMAIN:$HTTPS_PORT/api/status"
ping -c 3 "$LAPTOP1_IP"
```

**EXPECTED RESULT:** Name resolution and name-based HTTPS fail while IP reachability to Laptop 1 can still succeed. A separate `dig @"$DNS_IP" "$APP_DOMAIN" A` can succeed because it explicitly bypasses the wrong client setting; label it as a diagnostic query.

**NETWORK LAYER:** DNS is an application-layer service using UDP/TCP 53. The underlying LAN/IP path may remain healthy.

**WHY IT HAPPENS:** The client sends DNS questions to a machine without the required resolver. It cannot obtain the edge address from that resolver.

**HOW TO RESTORE:** On Laptop 2 run `./dns/set_client_dns.sh` without `--server`, then restore any project-owned scoped entry and flush/check using the commands below. Repeated setting changes preserve the original pre-project backup. Use `restore_client_dns.sh` only when leaving the project, since it restores the pre-project resolver rather than the project resolver.

If the managed Mac uses the project-owned scoped resolver, the fault command above changes that entry too; do not change unrelated resolver files. Restore its nameserver before flushing and checking HTTPS:

```sh
if [ -f "/etc/resolver/$TEAM_NAME.test" ]; then
  printf 'nameserver %s\nport 53\n' "$DNS_IP" | sudo tee "/etc/resolver/$TEAM_NAME.test"
fi
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
./scripts/test_dns.sh
./scripts/test_https.sh
```

## 2. DNS record points to the wrong IP — reference

**HOW TO BREAK:** On Laptop 1 point both project records to Laptop 1, where nginx is not deployed:

```sh
python3 dns/configure_dns.py --record-laptop 1 --check
./dns/restart_dns.sh
```

Flush both clients, then on either client:

```sh
dig @"$DNS_IP" "$APP_DOMAIN" A
curl --noproxy '*' --cacert "$TLS_ANCHOR" --connect-timeout 4 --max-time 10 \
  -v "https://$APP_DOMAIN:$HTTPS_PORT/api/status"
```

**EXPECTED RESULT:** DNS answers successfully but gives `LAPTOP1_IP`. The HTTPS connection goes to the wrong machine and fails at connection establishment when no service listens there. Record the observed result if another service unexpectedly occupies that port.

**NETWORK LAYER:** The configuration fault is at the DNS application layer; its visible consequence is a failed TCP connection to the wrong destination IP.

**WHY IT HAPPENS:** A valid DNS reply can contain the wrong address. Successful name resolution alone does not establish application correctness.

**HOW TO RESTORE:** On Laptop 1 regenerate the normal config without an override and restart:

```sh
python3 dns/configure_dns.py --check
./dns/restart_dns.sh
```

Flush both clients and run the DNS and HTTPS checks. This procedure changes only generated records, keeping `network.env` intact.

## 3. One backend stopped — live Option A used Backend A

**HOW TO BREAK:** On Laptop 1 stop only Backend A with Ctrl+C in its server terminal, or:

```sh
python3 scripts/_common.py service backend-a stop
```

From either client:

```sh
./scripts/test_load_balancing.sh --expect B --count 10
```

**EXPECTED RESULT:** nginx remains reachable over valid HTTPS and successful responses show `X-Backend: B`. A failed connection to A is retried on B for these safe read requests. Save Laptop 2's actual nginx error/access log excerpts.

**NETWORK LAYER:** Backend application availability with a refused or failed transport connection on the nginx-to-A hop.

**WHY IT HAPPENS:** The edge detects an unreachable upstream, skips it temporarily through passive failure accounting, and uses the remaining backend. Stopping the backend process leaves Laptop 1's DNS service available.

**HOW TO RESTORE:** On Laptop 1 run `python3 backend/backend_a.py` again. Allow more than five seconds for passive failure expiry, then run `./scripts/test_backends.sh` and `./scripts/test_load_balancing.sh`. Both A and B must reappear. You may also demonstrate B stopped with `service backend-b stop`, `--expect A`, and B's original launch command.

## 4. Both backends stopped — reference

**HOW TO BREAK:** Stop Backend A on Laptop 1 and Backend B on Laptop 2, keeping dnsmasq and nginx running:

```sh
# Laptop 1
python3 scripts/_common.py service backend-a stop
```

```sh
# Laptop 2
python3 scripts/_common.py service backend-b stop
./scripts/test_load_balancing.sh --expect unavailable --count 4
python3 scripts/_common.py diagnose
```

**EXPECTED RESULT:** DNS still points to Laptop 2 and TLS still validates, but HTTP returns **502 Bad Gateway** with an upstream-unavailable response. The normal HTTPS success check fails appropriately during this fault.

**NETWORK LAYER:** HTTP/application failure caused by failed transport connections to every upstream. Client-to-edge TCP/TLS can remain healthy.

**WHY IT HAPPENS:** nginx accepts the request but cannot obtain a response from either backend. DNS and certificate success do not imply backend availability.

**HOW TO RESTORE:** Restart A and B with their original Python commands on their respective laptops. Allow more than five seconds, then run direct-backend, HTTPS, load-balancing, and caching checks. Save the recovery results with the failure output.

## 5. Wrong destination port — reference

**HOW TO BREAK:** On Laptop 2 inspect actual listening ports with `lsof -nP -iTCP -sTCP:LISTEN`. Choose a currently unused TCP port that differs from every configured service port. On the client enter that observed port:

```sh
printf 'Enter the unused port you checked on Laptop 2: '
read WRONG_PORT
dig "$APP_DOMAIN" A
ping -c 3 "$LAPTOP2_IP"
curl --noproxy '*' --cacert "$TLS_ANCHOR" --connect-timeout 4 --max-time 10 \
  -v "https://$APP_DOMAIN:$WRONG_PORT/api/status"
```

**EXPECTED RESULT:** DNS and host reachability succeed; connecting to the unused port is refused or times out. State which result was actually observed and record the selected port.

**NETWORK LAYER:** TCP transport-layer endpoint selection.

**WHY IT HAPPENS:** An IP identifies a host; a port identifies the listening service. Correct DNS does not select the correct URL port automatically.

**HOW TO RESTORE:** Return to the configured port by running `./scripts/test_https.sh`. No service or configuration was modified for this fault.

## Finish

Run `./scripts/test_all.sh` on both laptops after any injected fault is restored. Save genuine screenshots and sanitized terminal output for the chosen live Option A demonstration, including restoration. At the end of the session restore original client DNS settings on both laptops, remove the project-owned MDM scoped entry if used, stop project services as described in the root guide, and remove certificate trust if appropriate using [the removal procedure](../tls/remove_certificate.md).
