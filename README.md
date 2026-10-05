# Computer Networks course project — Phase 1

Two members, two physical macOS laptops, one private service. Person A runs DNS, Backend A and the main client. Person B runs nginx, HTTPS, the load balancer, Backend B and the secondary client. See [ARCHITECTURE.md](ARCHITECTURE.md) for the topology.

The team uses two physical Macs and combines machine roles. The assignment's specific requirement asking two other Macs to use the DNS resolver cannot be literally demonstrated with two physical Macs and should be confirmed with faculty.

Code, templates, scripts and local tests are ready before deployment. The empty evidence directories are intentional: add real observations after both laptops are running. This guide covers Phase 1 only. Run commands from the repository root, the folder containing this README. Keep both laptops awake during demonstrations.

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
cp network.env.example network.env
nano network.env
```

Replace **every occurrence** of the Laptop 1 example address with its real address, and every occurrence of the Laptop 2 example address with its real address. The DNS and Backend A aliases must match Laptop 1; edge and Backend B aliases must match Laptop 2. Both Macs use the same values. Keep default ports 3001, 3002 and 8443 unless faculty agrees otherwise. The allowed edge substitutions are 8080/8443 instead of 80/443.

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

## STEP 12 — Test domain resolution

### RUN ON BOTH LAPTOPS

```sh
source <(python3 scripts/_common.py shell-env)
dig "$APP_DOMAIN" A
dig "$API_DOMAIN" A
./scripts/test_dns.sh
```

Expected: both A records contain the actual Laptop 2 `EDGE_IP`; the SERVER line identifies Laptop 1 `DNS_IP`. The script checks both project names over DNS UDP and TCP. `dig` tests DNS directly; the later HTTPS request also tests the actual application's resolver path.

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

The default preserves the assignment's permitted OpenSSL self-signed server-certificate route, with SANs for **both** app and api and 90-day validity. Private key permissions are restrictive. The script refuses to overwrite existing material. Optional `--local-ca` creates a CA and signed server certificate; confirm that local-CA route with faculty as required by Task E before choosing it. See [tls/README.md](tls/README.md).

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

Expected: trusted HTTPS for both app/api domains, HTTP200 and a backend identifier. Open the actual app domain with the configured HTTPS port in a browser as well; with default team/port the URL is `https://app.team1.test:8443`. Final application requests must use the domain.

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

## STEP 21 — Perform the five failure demos

Use [docs/FAILURE_ANALYSIS.md](docs/FAILURE_ANALYSIS.md): wrong client DNS, wrong DNS record, one backend stopped, both stopped, and wrong destination port. Inject one fault at a time and restore before continuing. Keep DNS/nginx running when stopping only backend processes. Collect real observations in `evidence/failures/`.

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

## GitHub Workflow

You can push the **code and configuration templates before live deployment**: backend source, DNS/nginx templates and scripts, TLS scripts, documentation, Wireshark instructions, empty evidence folders and `network.env.example`. The original assignment PDF stays outside this repository.

Do not commit `network.env`, TLS keys, generated certificates, PID files, logs, generated machine configs, temporary directories or `.DS_Store`. `.gitignore` covers them; source templates and documentation remain visible. Review what you stage:

```sh
git init -b main
git add .
git status --short
git diff --cached --stat
git commit -m "Prepare two-laptop Phase 1 networking project"
```

Create your empty GitHub repository, then use its actual URL:

```sh
printf 'Paste your actual GitHub repository URL: '
read -r GITHUB_REPO_URL
git remote add origin "$GITHUB_REPO_URL"
git push -u origin main
```

After deployment, add genuine screenshots, safe terminal `.txt` output and faculty-requested captures. Check for unrelated/private data before sharing. Then:

```sh
git add evidence
git diff --cached --stat
git commit -m "Add real Phase 1 deployment evidence"
git push
```

Every member should understand the complete system for the individual viva. [Concise notes](docs/VIVA_NOTES.md).
