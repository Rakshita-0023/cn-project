# Two-member / two-Mac Phase 1 architecture

```text
                   SAME LAN / HOTSPOT

          ┌──────────────────────────┐
          │                          │
     LAPTOP 1                   LAPTOP 2
     Person A                   Person B
     DNS                        nginx
     Backend A :3001            HTTPS/TLS :8443
     Main Client                Round-robin Load Balancer
                                Backend B :3002
                                Secondary Client
```

```text
Client
   ↓  DNS query for APP_DOMAIN
Laptop 1 DNS :53 UDP/TCP
   ↓  answer is Laptop 2 EDGE_IP
Client opens a separate TCP/TLS connection
   ↓
Laptop 2 nginx :HTTPS_PORT
   ↓  TLS termination; backend selection
 ┌──────────────┐
 ↓              ↓
Laptop 1       Laptop 2
Backend A      Backend B
:3001          :3002
   ↘            ↙
    nginx encrypts the response to the client
```

There are exactly two physical computers and two members, so DNS/backend/client roles share Laptop 1 and edge/backend/client roles share Laptop 2. Role combining is permitted by the assignment. The team uses two physical Macs and combines machine roles. The assignment's specific requirement asking two other Macs to use the DNS resolver cannot be literally demonstrated with two physical Macs and should be confirmed with faculty.

| Host | Service | Configuration |
|---|---|---|
| Laptop 1 / Person A | dnsmasq, DNS UDP/TCP53 | `DNS_IP = LAPTOP1_IP` |
| Laptop 1 / Person A | Backend A, HTTP TCP3001 by default | `BACKEND_A_IP = LAPTOP1_IP`, `BACKEND_A_PORT` |
| Laptop 2 / Person B | nginx, HTTPS TCP8443 by default; HTTP8080 redirect | `EDGE_IP = LAPTOP2_IP`, `HTTPS_PORT`; optional `HTTP_PORT` |
| Laptop 2 / Person B | Backend B, HTTP TCP3002 by default | `BACKEND_B_IP = LAPTOP2_IP`, `BACKEND_B_PORT` |

All deployment values come from the one ignored `network.env`. Reserved `.test` names are used. Both clients trust the public project certificate and resolve through Laptop 1. DNS supplies an address; it does not relay the HTTPS request. nginx hides backend addresses from normal application clients and forwards HTTP on separate TCP connections to its two equal-weight upstreams. [Full request flow](docs/REQUEST_FLOW.md).

Record actual IP, mask/prefix, gateway, interface and MAC address for both hosts with the inventory helper and save results to `evidence/lan/`. Both directions of ping must be observed on the actual laptops.

Co-located connections may use loopback. Laptop 1's self-DNS query and Laptop 2's self-HTTPS/backend connections will not all appear in a LAN-only capture; [capture both LAN and loopback](wireshark/README.md).

TLS ends at nginx. Backend HTTP is plaintext on the lab LAN. Stopping only one backend process permits nginx to retry another for the Phase 1 failure demo; stopping the whole laptop also loses its infrastructure roles. DNS on Laptop 1 and nginx on Laptop 2 are single points of failure. No redundant infrastructure is claimed.
