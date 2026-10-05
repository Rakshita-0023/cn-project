# Codexers edge on Laptop 2 / Person B

The recorded Type 2 deployment used Laptop 2 / Lakshya Choudhary at `10.7.31.46:8443` for HTTPS. App/API names were `app.codexers.test` and `api.codexers.test`; upstreams were `10.7.18.118:3001` (A) and `10.7.31.46:3002` (B). These are deployment notes; rendering still uses current `network.env` values.

The preserved nginx configuration is now a source template plus a renderer. It uses `BACKEND_A_IP:BACKEND_A_PORT` and `BACKEND_B_IP:BACKEND_B_PORT`, default equal-weight round robin, TLS termination and an HTTP-to-HTTPS redirect. Normal app access is by `APP_DOMAIN` or `API_DOMAIN` over `HTTPS_PORT`.

```sh
python3 nginx/configure_nginx.py
./tls/generate_certificate.sh
./nginx/start_nginx.sh
./scripts/test_https.sh
./scripts/test_load_balancing.sh
```

Generate the certificate only once; when it already exists, retain it and skip the generation command. Trust it on both clients as described in the root guide. The start script runs `nginx -t` with the project's explicit config/prefix before launching. Certificate/config failures prevent launch. Global Homebrew configs are not changed.

Generated file: ignored `nginx/generated/nginx.conf`. Project logs, PID and temporary directories: ignored `nginx/runtime/`. Logs record actual client/socket, TLS version, upstream address/status, backend identifier and elapsed time. `X-Edge: Laptop-2` identifies the edge. Required forwarded headers are Host, X-Real-IP, X-Forwarded-For and X-Forwarded-Proto; X-Forwarded-Port is also supplied.

Stop: `./nginx/stop_nginx.sh`. After rendering a change, use `./nginx/reload_nginx.sh`; it validates the candidate before signaling the verified project master. For privileged ports the script requests sudo when needed.

Passive failure detection uses `max_fails=1`, `fail_timeout=5s` and bounded retries for safe read requests. **Live submission demo used Option A — Stop Backend A**: B continued serving, then A/B selection resumed after restoration. Both upstreams unavailable yields a clear HTTP502 JSON response, retained as a reference scenario rather than a claimed live result. A healthy quiet single worker alternates; concurrent traffic can change the sequence. A restarted backend may need more than five seconds before rejoining selection.

If `nginx -V` lists `--with-http_v2_module` and nginx is at least1.25.1, `python3 nginx/configure_nginx.py --http2` enables HTTP/2. Validate/reload, then show actual negotiation using curl `--http2` with the trusted certificate. HTTP/1.1 remains required; HTTP/3 is explanation-only.
