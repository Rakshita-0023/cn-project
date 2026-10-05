# Backend services

Person A runs `python3 backend/backend_a.py` on Laptop 1; Person B runs `python3 backend/backend_b.py` on Laptop 2. Run from the root; the shell start scripts also work from other directories. Both bind IPv4 `0.0.0.0`, which makes them LAN-accessible. Ports come from `network.env`; without that file the entry points default to 3001/3002, enabling a quick local backend check.

`backend_a.py` contains the preserved shared HTTP implementation; `backend_b.py` imports it and selects identifier B. There are no copied implementations to maintain.

| Endpoint | Behavior |
|---|---|
| GET `/` | JSON service confirmation, backend identifier and status |
| GET `/api/status` | JSON backend identifier/status, `Cache-Control: no-store` |
| GET/HEAD `/cache-demo` | Shared body, `Cache-Control: public, max-age=60`, ETag |
| Conditional `/cache-demo` | Matching `If-None-Match` returns 304 with no body |
| `/api/cache` | Preserved compatible alias for the cache endpoint |

Every normal response identifies A/B in `X-Backend`. Both instances share the same cache representation and ETag so validation remains correct across nginx round robin. HEAD exposes representation headers without a body. Unknown paths return404. HTTP/1.1 is supported using Python's standard library.

Start in a dedicated terminal with the Python entry point or `./backend/start_backend_a.sh` / `./backend/start_backend_b.sh`. Stop using Ctrl+C or `python3 scripts/_common.py service backend-a stop` / `backend-b stop`. PID files are isolated under ignored `backend/runtime/`; existing project services and unrelated PID reuse are checked.

Run `./scripts/test_backends.sh` after both processes are deployed. Direct backend tests are administrative checks; the app demo goes through the domain and nginx. `./scripts/test_all.sh --local -v` runs isolated development regressions before deployment.
