# Example configuration renders

These specimens were rendered from the original `network.env.example` using
`python3 phase2/network.py --config network.env.example render --all`.
They use the generic team1/example LAN addresses, not a verified deployment.
Absolute project paths and user IDs are normalized for review. Source templates
and `network.env` are authoritative; regenerate separately on each Mac before
using any configuration. The startup command checks actual service syntax and
refuses conflicting listeners. No certificate or private key is included here.

- `dns-primary-dnsmasq.conf`: Mac 1 listener and exact project records.
- `dns-backup-dnsmasq.conf`: Mac 2 listener, matching records and TTL.
- `edge-primary-nginx.conf`: Mac 2 TLS entry point and HA upstreams.
- `edge-standby-nginx.conf`: Mac 1 TLS standby and identical HA behavior.
- `backend-isolation.pf`: default worker UID and both-host guard.

PF syntax was checked against the actual generated file with macOS `pfctl -n`;
normalizing paths does not certify live enforcement. Use `make firewall` only
after reviewing the local generated rules and keeping `make rollback` ready.
