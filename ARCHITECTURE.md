# Codexers — Type 2 Phase 1 architecture

This project uses Type 2 infrastructure: two physical macOS laptops with combined roles, as supported by the Phase 1 submission form. Polana Rakshita is Person A; Lakshya Choudhary is Person B. Roles share hosts because there are two physical Macs.

The addresses below are the **actual IPs used during the recorded Phase 1 deployment**. They can change on another LAN; update the ignored `network.env` and render configurations locally when redeploying.

```text
                   SAME LAN

        ┌───────────────────────────┐
        │                           │
   LAPTOP 1                    LAPTOP 2
   Person A                    Person B
   10.7.18.118                 10.7.31.46
   DNS :53                     nginx / TLS :8443
   Backend A :3001             Round-robin Load Balancer
   Main Client                 Backend B :3002
                               Secondary Client
```

```text
Client
  ↓  query / response
Laptop 1 DNS (10.7.18.118:53)
  ↓  app.codexers.test → 10.7.31.46
Client opens a separate TCP/TLS connection
  ↓
Laptop 2 nginx :8443
  ↓  TLS termination and round-robin selection
 ┌───────────────────┐
 ↓                   ↓
Backend A            Backend B
10.7.18.118:3001      10.7.31.46:3002
      ↘             ↙
       nginx returns the response over TLS
```

| Host | Recorded service | Runtime configuration |
|---|---|---|
| Laptop 1 / Person A | dnsmasq, UDP/TCP 53 | `DNS_IP = LAPTOP1_IP = 10.7.18.118` |
| Laptop 1 / Person A | Backend A, HTTP :3001 | `BACKEND_A_IP = LAPTOP1_IP`, `BACKEND_A_PORT=3001` |
| Laptop 2 / Person B | nginx, HTTPS :8443; HTTP :8080 redirect | `EDGE_IP = LAPTOP2_IP = 10.7.31.46`, `HTTPS_PORT=8443` |
| Laptop 2 / Person B | Backend B, HTTP :3002 | `BACKEND_B_IP = LAPTOP2_IP`, `BACKEND_B_PORT=3002` |

Both `app.codexers.test` and `api.codexers.test` resolve privately to Laptop 2. Public Google DNS returned NXDOMAIN for `app.codexers.test`. DNS supplies an address; it does not relay HTTPS. nginx is the normal application entry point and makes separate HTTP connections to the two equal-weight backends. Client-to-edge TLS ends at nginx; backend HTTP is plaintext on the lab LAN. [Full request flow](docs/REQUEST_FLOW.md).

Both laptops also serve as test clients. The reported deployment confirmed ping in both directions, trusted HTTPS, A/B selection, `/cache-demo` headers and conditional 304, and DNS/TCP/TLS captures. The captured client-to-edge TCP connection used `10.7.18.118:59218 → 10.7.31.46:8443`; 59218 was an ephemeral source port for that connection, not a fixed service port.

Co-located requests can appear on loopback rather than Wi-Fi. Laptop 1's self-DNS and Laptop 2's self-edge/backend traffic may be missed by a LAN-only capture. [Wireshark instructions](wireshark/README.md) cover both interfaces and the recorded packet details. On the managed Mac, a [domain-specific resolver](dns/README.md#managed-mac--mdm-dns-override) selected Laptop 1 for `codexers.test` while leaving unrelated DNS under normal macOS/MDM settings.

**Live submission demo used Option A — Stop Backend A.** DNS, TCP/TLS to nginx, nginx and Backend B continued working. Restarting Backend A restored A/B round robin. Stopping the backend process preserves Laptop 1's DNS; switching off that laptop would remove both roles. DNS and nginx remain single infrastructure instances in this Type 2 deployment.

The [evaluation checklist](docs/EVALUATION_CHECKLIST.md) records reported live completion. Attach the team's real artifacts using [the evidence index](evidence/README.md); documentation of a result is not a claim that its screenshot or capture is already committed.
