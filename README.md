# Computer Networks Phase 1 — Codexers

## Team

**Team Name:** Codexers

**Infrastructure:** Type 2 — 2 physical macOS laptops with combined roles

### Members

- **Rakshita Polana — `<ENROLLMENT_NUMBER>` — Person A**
  - Private DNS server
  - Backend A
  - Main client/testing
  - Wireshark / DNS / TCP / TLS evidence
- **Lakshya Choudhary — `<ENROLLMENT_NUMBER>` — Person B**
  - nginx reverse proxy
  - HTTPS/TLS
  - Load balancer
  - Backend B
  - Client/testing

This project uses Type 2 infrastructure: two physical macOS laptops with combined roles, as supported by the Phase 1 submission form's category **“Type 2 — 2 or 3 Macs with combined roles.”**

## Completed Live Deployment

| Host | Recorded LAN IP | Roles |
|---|---|---|
| Laptop 1 / Person A | `10.7.18.118` | dnsmasq, Backend A :3001, main client/testing |
| Laptop 2 / Person B | `10.7.31.46` | nginx, HTTPS :8443, round-robin balancing, Backend B :3002, client/testing |

The team completed LAN connectivity, private DNS, public-DNS NXDOMAIN comparison, validated HTTPS, A/B balancing, caching with ETag/304, DNS/TCP/TLS Wireshark captures, and the Backend A stop-and-restore failure demo. These are the team's reported live results; [the checklist](docs/EVALUATION_CHECKLIST.md) records them. Six original screenshots are now attached: two ping results, TCP and TLS Wireshark views, and a clearly labeled background TLS view. [The evidence index](evidence/README.md) links every attached file and identifies the remaining evidence to attach.

Actual service names are `app.codexers.test` and `api.codexers.test`. These IPs belong to the recorded deployment and can change on another LAN. The [architecture](ARCHITECTURE.md) and [configuration bundle](docs/CONFIGURATION_BUNDLE.md) describe the same two-laptop setup. HTTP caching is demonstrated on `/cache-demo`.

Use [Phase 1 Final Demo Commands](#phase-1-final-demo-commands) for the recording and the deployment steps below when recreating the setup. Run commands from the repository root, the folder containing this README. Keep both laptops awake during demonstrations. Reuse the existing working runtime configuration and certificates during the live session.

## STEP 1 — Connect both Macs to the same Wi-Fi/LAN/hotspot

### RUN ON BOTH LAPTOPS

Connect to the same private network. A hotspot or access point must permit traffic between clients. Copy this repository onto both Macs.

## STEP 2 — Find both IP addresses

### RUN ON BOTH LAPTOPS

```sh
ipconfig getifaddr en0
networksetup -listallhardwareports
```

Use the Device listed under Wi-Fi if it is not `en0`: run `ipconfig getifaddr` with that actual device name. Share both IPs. Record IPv4, mask/prefix, gateway, interface and MAC address. The retained inventory helper saves actual observations:

### RUN ON LAPTOP 1

```sh
python3 scripts/_common.py inventory --laptop 1
```

### RUN ON LAPTOP 2

```sh
python3 scripts/_common.py inventory --laptop 2
```

If the default route uses a VPN or different interface, pass `--interface` with the actual Wi-Fi device. If Python 3 is absent, install it as described in Step 5, then run these inventory commands. Results go to `evidence/lan/`.

## STEP 3 — Ping both directions

### RUN ON LAPTOP 1

```sh
printf 'Enter Laptop 2 actual LAN IPv4: '
read -r LAPTOP2_IP
ping -c 3 "$LAPTOP2_IP"
```

### RUN ON LAPTOP 2

```sh
printf 'Enter Laptop 1 actual LAN IPv4: '
read -r LAPTOP1_IP
ping -c 3 "$LAPTOP1_IP"
```

Expected: replies from the peer and no packet loss on a healthy LAN. If ping fails, fix connectivity before proceeding. These prompts collect actual addresses; no example IP is used in commands.

## STEP 4 — Create runtime config

### RUN ON BOTH LAPTOPS

```sh
if [ ! -f network.env ]; then
  cp network.env.example network.env
fi
nano network.env
```

`network.env.example` intentionally contains generic example values. For Codexers, set `TEAM_NAME=Codexers`, `APP_DOMAIN=app.codexers.test` and `API_DOMAIN=api.codexers.test`. Replace **every occurrence** of each example laptop address: Laptop 1 used `10.7.18.118`, and Laptop 2 used `10.7.31.46` in the recorded deployment. Use their current real addresses on another LAN. The DNS and Backend A aliases must match Laptop 1; edge and Backend B aliases must match Laptop 2. Both Macs use the same values, with backend ports 3001/3002 and HTTPS 8443. [All recorded variables](docs/CONFIGURATION_BUNDLE.md#recorded-deployment-variables).

`network.env` is the **only editable runtime configuration** and is ignored by Git. Templates require no manual IP substitution. Set `TEAM_NAME`, `APP_DOMAIN` and `API_DOMAIN` together if you change the team name; use `.test`, not `.local`.

```sh
python3 scripts/_common.py validate
source <(python3 scripts/_common.py shell-env)
```

If Python 3 is absent, run these two commands after installing it in Step 5.

Expected: `PASS: network.env is consistent with the two-laptop architecture`. Repeat the `source` command in new testing/capture terminals; it emits safely quoted, validated variables for Bash or zsh. Service/test scripts read the file themselves and work from any directory.

Without optional `UPSTREAM_DNS`, project DNS answers only project names; unrelated Internet DNS will stop working while clients use it. For Internet access, add `UPSTREAM_DNS` with your actual independent router/approved resolver IPs, comma separated. Do not use either laptop as an upstream. [Configuration details](docs/CONFIGURATION_BUNDLE.md).

## STEP 5 — Install required software

### RUN ON LAPTOP 1

```sh
brew install dnsmasq
```

### RUN ON LAPTOP 2

```sh
brew install nginx
```

### RUN ON BOTH LAPTOPS

```sh
python3 --version
openssl version
curl --version
brew install --cask wireshark
```

Install Wireshark now while normal Internet DNS is available; Step 20 starts capture after the services are ready.

Use Python 3.9 or later and OpenSSL 3 or later. If missing, install `brew install python openssl`. If `openssl version` reports Apple's older LibreSSL, use the Homebrew version:

```sh
export PATH="$(brew --prefix openssl)/bin:$PATH"
```

Homebrew must already be installed. Inspect `brew services list` for conflicting default services; the project scripts use isolated configs instead of editing Homebrew global configs. `dnsmasq` is found even when its Homebrew `sbin` directory is not in PATH.

## STEP 6 — Start Backend A on Laptop 1

### RUN ON LAPTOP 1

In a dedicated terminal:

```sh
python3 backend/backend_a.py
```

Expected with default config: `Backend A: HTTP/1.1 on 0.0.0.0:3001`. Leave the terminal open. Equivalent wrapper: `./backend/start_backend_a.sh`.

## STEP 7 — Start Backend B on Laptop 2

### RUN ON LAPTOP 2

In a dedicated terminal:

```sh
python3 backend/backend_b.py
```

Expected with default config: `Backend B: HTTP/1.1 on 0.0.0.0:3002`. Leave it open. Equivalent wrapper: `./backend/start_backend_b.sh`.

## STEP 8 — Test both backends directly

### RUN ON BOTH LAPTOPS

In a separate terminal:

```sh
./scripts/test_backends.sh
```

Expected: both direct endpoints return HTTP200, JSON status `ok`, and the matching `X-Backend: A` or `B`; the script prints PASS. Direct IP requests are administrative backend checks. The final application demo uses its domain through nginx.

## STEP 9 — Generate DNS config on Laptop 1

### RUN ON LAPTOP 1

```sh
python3 dns/configure_dns.py --check
```

Creates ignored `dns/generated/dnsmasq.conf` from the template and `network.env`. Both app/api names point to `EDGE_IP`. Expected: successful render and dnsmasq syntax check.

## STEP 10 — Start dnsmasq

### RUN ON LAPTOP 1

```sh
./dns/start_dns.sh
```

The script validates syntax before starting, requests administrator privileges for port53, and uses project-only PID/log files under `dns/runtime/`. Expected: `PASS: project dns running with PID ...` with the actual PID. No DHCP service is enabled.

## STEP 11 — Configure client DNS

### RUN ON BOTH LAPTOPS

```sh
./dns/set_client_dns.sh
scutil --dns
```

The script detects the macOS Wi-Fi network service, prints the old/new DNS settings, saves the original settings and points the client at `DNS_IP`. If detection is ambiguous, run `networksetup -listallnetworkservices` and pass `--service` with the exact active service name. Repeated setup does not overwrite the original backup. Browser DoH/Secure DNS or VPN overrides can bypass this setting; use system DNS for the project and confirm the actual path in capture.

On the managed Mac, `networksetup` showed the project DNS but `scutil --dns` still showed institutional/public resolvers. Apply [Managed Mac / MDM DNS Override](dns/README.md#managed-mac--mdm-dns-override) only if this happens; it supplements this normal workflow with a domain-specific resolver.

## STEP 12 — Test domain resolution

### RUN ON BOTH LAPTOPS

```sh
source <(python3 scripts/_common.py shell-env)
dig "$APP_DOMAIN" A
dig "$API_DOMAIN" A
./scripts/test_dns.sh
```

Expected: both A records contain Laptop 2 `EDGE_IP`, recorded as `10.7.31.46`. The script explicitly queries Laptop 1 `DNS_IP` over UDP and TCP. With normal client DNS, dig's SERVER line identifies Laptop 1. With the MDM scoped resolver, ordinary dig may still use the default resolver; use `dig @"$DNS_IP" "$APP_DOMAIN" A` for the private-server query and `dscacheutil -q host -a name "$APP_DOMAIN"` to verify macOS application resolution. The later HTTPS request uses that application resolver path.

## STEP 13 — Generate nginx config on Laptop 2

### RUN ON LAPTOP 2

```sh
python3 nginx/configure_nginx.py
```

Creates ignored `nginx/generated/nginx.conf` with equal-weight backends, forwarding headers, HTTP redirect and HTTPS. Paths point to this laptop's local project, so generate separately after moving the repository. Logs/PID/temp files are under `nginx/runtime/`.

## STEP 14 — Generate TLS certificate

### RUN ON LAPTOP 2

```sh
./tls/generate_certificate.sh
openssl x509 -in tls/certs/server.crt -noout -subject -dates -ext subjectAltName
```

These commands are for a new deployment; retain existing working certificate material for the final demo. The default generates an OpenSSL self-signed server certificate with SANs for **both** app and api and 90-day validity. Private key permissions are restrictive, and existing material is never silently overwritten. Optional `--local-ca` creates a CA and signed server certificate. See [tls/README.md](tls/README.md).

## STEP 15 — Trust the certificate

Copy Laptop 2's public `tls/certs/server.crt` into the same location on Laptop 1 (AirDrop is fine). For the optional CA route, also copy public `ca.crt`. Keep private keys on Laptop 2.

### RUN ON BOTH LAPTOPS

```sh
./tls/trust_certificate.sh
```

The script shows the certificate fingerprint and adds the public anchor to System Keychain. Verify fingerprints agree on both Macs. Browser HTTPS should show no certificate warning. Test scripts also supply the public anchor explicitly with `--cacert`, which validates trust, hostname and expiry; they never bypass validation.

## STEP 16 — Start nginx

### RUN ON LAPTOP 2

```sh
./nginx/start_nginx.sh
```

The script runs **nginx -t before starting** and fails clearly if validation fails. Expected: syntax/configuration checks succeed and a project PID is reported. If ports80/443 are selected and require privileges, the script requests sudo.

## STEP 17 — Test HTTPS

### RUN ON BOTH LAPTOPS

```sh
./scripts/test_https.sh
```

Expected: trusted HTTPS for both app/api domains, HTTP200 and a backend identifier. The recorded app URL is `https://app.codexers.test:8443`. Final application requests use the domain name and validate the certificate; never use `curl -k`.

## STEP 18 — Test load balancing

### RUN ON BOTH LAPTOPS

```sh
./scripts/test_load_balancing.sh
```

Expected: request lines containing both `X-Backend: A` and `X-Backend: B`, followed by PASS. Equal weights round robin alternates in a quiet healthy system. Other requests/failures can change observed order; optional `--strict` checks strict alternation for the quiet demonstration.

## STEP 19 — Test caching

### RUN ON BOTH LAPTOPS

```sh
./scripts/test_caching.sh
./scripts/test_all.sh
```

Expected: `Cache-Control: public, max-age=60`, an actual ETag, a first HTTP200 and a conditional HTTP304 with no body. The same representation/ETag is served by both backends, so conditional requests work through round robin. Repeating curl alone is not evidence of browser cache reuse. `test_all.sh` runs ping, direct backends, DNS, HTTPS, balancing and caching; run it on both laptops to prove both ping directions.

## STEP 20 — Open Wireshark and capture evidence

### RUN ON BOTH LAPTOPS

```sh
open -a Wireshark
```

Follow [wireshark/README.md](wireshark/README.md) for exact capture commands and [filters.md](wireshark/filters.md) for analysis. Capture the real LAN interface **and loopback**: roles are co-located. Show DNS, SYN/SYN-ACK/ACK, TLS ClientHello/ServerHello/certificate, encrypted application data, ports and TCP sequence/ACK/window values. Use an additional validated TLS1.2 request for visible Certificate/ChangeCipherSpec; explain TLS1.3's encrypted handshake. Save actual captures/screenshots to `evidence/wireshark/`.

## STEP 21 — Perform the selected failure demo

The submission form requires one selected Phase 1 failure demonstration. **Live submission demo used Option A — Stop Backend A.** Before the stop, nginx alternated A/B; while A was stopped, B served all requests; after restarting A, balancing resumed. Keep DNS, nginx and Backend B running. [FAILURE_ANALYSIS.md](docs/FAILURE_ANALYSIS.md) records this demonstration and retains four other reference scenarios without claiming they were demonstrated live.

## STEP 22 — Save evidence inside evidence/

See [evidence/README.md](evidence/README.md) for what belongs in each of the eight folders. Capture commands/logging do not run automatically during local tests. Include genuine outputs, screenshots, packet numbers, failure explanations and restored baselines. [Evaluation checklist](docs/EVALUATION_CHECKLIST.md).

## STEP 23 — Restore normal DNS settings

### RUN ON BOTH LAPTOPS

```sh
./dns/restore_client_dns.sh
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

Expected: exactly the previous manual DNS addresses or DHCP/automatic DNS is restored. The saved backup is removed only after the change succeeds. Certificate removal instructions are in [tls/remove_certificate.md](tls/remove_certificate.md).

If you created `/etc/resolver/codexers.test` for the MDM workaround, also follow its [cleanup instructions](dns/README.md#cleanup) and flush DNS again. Restoring network-service DNS alone does not remove that scoped file.

## STEP 24 — Stop project services cleanly

### RUN ON LAPTOP 1

```sh
./dns/stop_dns.sh
python3 scripts/_common.py service backend-a stop
```

### RUN ON LAPTOP 2

```sh
./nginx/stop_nginx.sh
python3 scripts/_common.py service backend-b stop
```

Alternatively stop the foreground backend with Ctrl+C in its terminal. Stop scripts target only verified project PIDs; they do not use broad `killall nginx`/`killall dnsmasq` commands. Keep the evidence and reviewed configuration bundle for evaluation.

## Local development verification

```sh
./scripts/test_all.sh --local -v
```

This runs the relocated standard-library tests, real temporary backend/nginx/DNS processes, certificate validation, caching and failure recovery on loopback with ephemeral ports. It requires nginx, dnsmasq, OpenSSL and curl on the development Mac; install missing test dependencies if integration tests report skips. These tests create no physical deployment evidence and do not change system DNS or Keychain. `scripts/_common.py` centralizes the shared parser/helpers; `scripts/test_local.py` retains the local regression tests without adding another top-level folder.

Retained helper commands: `python3 scripts/_common.py diagnose` checks DNS→TCP→TLS→HTTP; `python3 scripts/_common.py bundle` writes an ignored source/evidence zip under `scripts/runtime/`, excluding private material and machine-specific config.

## Phase 1 Final Demo Commands

Run these on the deployed LAN after configuring system DNS and certificate trust. Use the existing public trust anchor if your curl build does not read macOS Keychain: add `--cacert tls/certs/server.crt`, or `--cacert tls/certs/ca.crt` for the CA route. This retains certificate and hostname validation. Never use `-k`.

### DNS

```sh
dig app.codexers.test
dig @8.8.8.8 app.codexers.test
```

The private resolver returns `10.7.31.46`; Google public DNS returned `NXDOMAIN` for the private `.test` name. If using the managed-Mac scoped resolver, show these additional checks because dig does not use macOS's domain-specific resolver routing:

```sh
dig @10.7.18.118 app.codexers.test
dscacheutil -q host -a name app.codexers.test
```

### HTTPS

```sh
curl -v https://app.codexers.test:8443
```

Show successful certificate validation and HTTP response. Access by domain name, not by IP.

### Load balancing

```sh
for i in {1..6}; do \
  echo "Request $i"; \
  curl -s -D - -o /dev/null \
  https://app.codexers.test:8443/api/status | \
  grep -i "X-Backend"; \
done
```

Expected: both A and B appear, alternating on a quiet healthy system.

### Caching

**HTTP caching is demonstrated on `/cache-demo`.**

```sh
curl -sI https://app.codexers.test:8443/cache-demo
./scripts/test_caching.sh
```

Expected headers include `Cache-Control: public, max-age=60`, `ETag: "..."`, `X-Backend: A` or `B`, and `Date`. The dots indicate the actual tag to read from the response; they are not a value to send. The script extracts the real ETag, sends it in `If-None-Match`, and verifies `304 Not Modified` with no body. `/api/status` intentionally returns `Cache-Control: no-store` so caching does not hide backend selection. [Cache request flow](docs/REQUEST_FLOW.md#cache-path).

### Failure demo

Stop Backend A with **Ctrl+C in its Laptop 1 terminal**. Run the load-balancing loop again: expected `X-Backend: B` only. DNS, client-to-nginx TCP, TLS, nginx and Backend B remain working.

Restart on Laptop 1:

```sh
python3 backend/backend_a.py
```

Allow more than five seconds for nginx's passive failure window, then repeat the loop: A and B both return. Laptop 2's backend launch command remains:

```sh
python3 backend/backend_b.py
```

## 5-Minute Demo Recording

Name the file **`CN_Phase1_[Section]_Codexers_Type2.mp4`**, replacing `[Section]` with your actual section.

| Time | Show |
|---|---|
| 0:00–2:00 | Team introduction, Type 2 architecture, actual LAN IPs/ping, private DNS and public NXDOMAIN |
| 2:00–4:00 | Validated HTTPS, nginx, A/B balancing, `/cache-demo` and 304, Wireshark DNS/TCP/TLS |
| 4:00–5:00 | Stop Backend A → only Backend B → restore Backend A and A/B selection |

- Do not use `curl -k`.
- Access the service by domain name, not IP.
- Show actual terminal output and recorded packets.
- Maximum duration: **5 minutes**; maximum file size: **500 MB**.
- Upload to Google Drive with access set to **anyone with the link**, verify access, then submit the link in the Google Form.

Video upload and Google Form submission remain unchecked in [the checklist](docs/EVALUATION_CHECKLIST.md). Both members should understand the full system for the individual viva; use [the notes](docs/VIVA_NOTES.md).

## GitHub Workflow

The repository is [Rakshita-0023/cn-project](https://github.com/Rakshita-0023/cn-project), with branch `main`. Commit source, templates, documentation, and reviewed genuine evidence. The original assignment PDF stays outside this repository.

Do not commit `network.env`, TLS keys, generated certificates, PID files, logs, generated machine configs, DNS backups, temporary directories or `.DS_Store`. The current `.gitignore` covers these while keeping source templates, `network.env.example`, documentation, and safe evidence PNG/text files visible.

```sh
git switch main
git add .
git diff --cached --check
git diff --cached --stat
git status --short
git commit -m "Polish Codexers Phase 1 submission documentation"
git push origin main
```

When attaching real evidence, review each file first, then use `git add evidence`, review the staged diff, commit and push. Exclude unrelated personal traffic and private material. Do not replace missing captures with sample output. Enrollment numbers and the final video section label must be filled manually.
