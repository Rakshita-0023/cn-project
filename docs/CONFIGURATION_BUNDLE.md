# Phase 1 configuration bundle

Run commands from the repository root. The [deployment guide](../README.md) gives the complete order. All deployment addresses come from your uncommitted `network.env`; configuration templates stay portable.

## Variables and roles

| Variable | Meaning |
|---|---|
| `TEAM_NAME` | Private team label; the example is `team1` |
| `LAPTOP1_IP` | Person A's real LAN address |
| `LAPTOP2_IP` | Person B's real LAN address |
| `DNS_IP`, `BACKEND_A_IP` | Both equal `LAPTOP1_IP` |
| `EDGE_IP`, `BACKEND_B_IP` | Both equal `LAPTOP2_IP` |
| `BACKEND_A_PORT`, `BACKEND_B_PORT` | Backend ports, default 3001 and 3002 |
| `APP_DOMAIN`, `API_DOMAIN` | `app.<TEAM_NAME>.test` and `api.<TEAM_NAME>.test` |
| `HTTPS_PORT` | TLS edge port, default 8443 |
| Optional `HTTP_PORT` | HTTP redirect listener, default 8080 |
| Optional `DNS_TTL` | Ordinary DNS record lifetime, default 30 seconds |
| Optional `UPSTREAM_DNS` | Comma-separated independent resolvers for unrelated names; empty means only project DNS names resolve |

The parser rejects shell expressions, inconsistent role addresses, malformed domains, and overlapping ports. Parse values for terminal commands without executing the file:

```sh
python3 scripts/_common.py validate
source <(python3 scripts/_common.py shell-env)
```

## Laptop 1: dnsmasq

```sh
python3 dns/configure_dns.py --check
./dns/start_dns.sh
```

The renderer creates `dns/generated/dnsmasq.conf` from [the template](../dns/dnsmasq.conf.template). Both app and API A records point to `EDGE_IP`, which is Laptop 2. dnsmasq listens on Laptop 1's configured address on UDP/TCP 53. It does not provide DHCP or read system hosts files. Logs and PID are isolated in `dns/runtime/`.

On each client, `./dns/set_client_dns.sh` selects the actual Wi-Fi network service, saves its original DNS settings, and sets `DNS_IP`. `./dns/restore_client_dns.sh` restores that saved state. The saved state belongs to that particular Mac; do not copy it between laptops.

## Laptop 2: nginx

```sh
python3 nginx/configure_nginx.py
./nginx/start_nginx.sh
```

Generate and trust TLS material before starting nginx. The renderer creates `nginx/generated/nginx.conf` from [the template](../nginx/nginx.conf.template). Its upstream contains `BACKEND_A_IP:BACKEND_A_PORT` and `BACKEND_B_IP:BACKEND_B_PORT` with equal weights, using nginx's default round robin. Both hostnames use this pool. HTTP redirects to the HTTPS port. The proxy forwards `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto`.

Project PID, logs, and temporary files are under `nginx/runtime/`. The start and reload scripts run `nginx -t` against this exact configuration first. Read requests can retry a failed upstream; passive failure accounting excludes a failed backend for five seconds. When both are unavailable, nginx returns HTTP 502. This is one edge process on one physical laptop.

HTTP/1.1 is the mandatory working baseline. If installed nginx is version 1.25.1 or newer and includes its HTTP/2 module, the retained optional `python3 nginx/configure_nginx.py --http2` enables HTTP/2; use `--check` after generating certificates. Record any negotiated protocol actually observed. Do not claim HTTP/3 is implemented.

## TLS

On Laptop 2:

```sh
./tls/generate_certificate.sh
openssl x509 -in tls/certs/server.crt -noout -subject -dates -ext subjectAltName
```

The default is a self-signed server certificate with both configured domains in its Subject Alternative Names. The preserved optional `--local-ca` generates a private local CA and a signed server certificate; see [TLS instructions](../tls/README.md) for its assignment approval condition. Neither route produces a CN-only certificate. nginx supports TLS 1.2 and TLS 1.3.

Copy only the public trust certificate to Laptop 1: `server.crt` for the default route, or `ca.crt` for the optional CA route. On both laptops run `./tls/trust_certificate.sh` and verify browser trust. Test scripts also use the appropriate public anchor with `curl --cacert`; certificate identity and trust remain checked. Private keys stay on Laptop 2 and out of Git.

## Backends and verification

Laptop 1:

```sh
python3 backend/backend_a.py
```

Laptop 2:

```sh
python3 backend/backend_b.py
```

Both bind `0.0.0.0`, expose `/`, `/api/status`, and `/cache-demo`, and identify themselves with `X-Backend`. The retained `/api/cache` alias behaves identically to `/cache-demo`. The cache representation and ETag match across backends, permitting a valid 304 even when nginx chooses a different backend for revalidation.

On each laptop after complete setup:

```sh
./scripts/test_all.sh
```

The independently runnable checks cover ping, direct backends, UDP/TCP DNS, validated HTTPS, both backend selections, and 200-to-304 caching. Local automated checks run with `./scripts/test_all.sh --local -v` without changing real DNS settings or Keychain trust.

## Submission material

Keep source and templates in Git. Add genuine, reviewed evidence after deployment using [the evidence index](../evidence/README.md). Generated configs contain local paths and addresses and are ignored. If faculty requests a configuration bundle, share reviewed generated DNS/nginx configs separately with the public certificate, backend commands, and actual inventory; exclude keys and saved client DNS state. `python3 scripts/_common.py bundle` produces a source archive under ignored `scripts/runtime/` and excludes runtime secrets.

The team uses two physical Macs and combines machine roles. The assignment's specific requirement asking two other Macs to use the DNS resolver cannot be literally demonstrated with two physical Macs and should be confirmed with faculty.
