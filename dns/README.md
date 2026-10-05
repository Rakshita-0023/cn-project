# DNS on Laptop 1 / Person A

`configure_dns.py` reads root `network.env` as data and renders `dnsmasq.conf.template` to ignored `dns/generated/dnsmasq.conf`. `APP_DOMAIN` and `API_DOMAIN` both map to `EDGE_IP` on Laptop 2. Never edit example IPs inside a template.

```sh
python3 dns/configure_dns.py --check
./dns/start_dns.sh
./dns/set_client_dns.sh
./scripts/test_dns.sh
```

Run the server commands on Laptop 1 only. Run `set_client_dns.sh` on **both** laptops. DNS listens on Laptop 1's actual IPv4, UDP and TCP53. This is a DNS-only service with no DHCP. It ignores the system resolver file to prevent forwarding loops; optional independent `UPSTREAM_DNS` entries permit unrelated Internet resolution. Without upstreams it serves project-only names. Normal project records have TTL30 by default, configurable through optional `DNS_TTL`.

The start script validates syntax first, asks for sudo for the DNS service, and keeps a verified project PID/log in `dns/runtime/`. Stop with `./dns/stop_dns.sh`; restart with `./dns/restart_dns.sh`. Restart uses the current generated file and does not silently erase a controlled wrong-record fault. Re-run the configurator without fault options to restore the normal record.

Client DNS setup detects the Wi-Fi network service, saves exact previous addresses (including IPv6) or automatic/DHCP state, prints the change, then sets `DNS_IP`. For Ethernet, ambiguous detection or another active service, pass `--service` with the exact name shown by `networksetup -listallnetworkservices`. One outstanding backup is kept per laptop; repeated setup/fault tests preserve that original backup.

```sh
./dns/restore_client_dns.sh
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

Restore uses the saved service and addresses, or `Empty` for DHCP. It removes the backup only on success. Do not manually discard the backup before restoration. Generated config/backup/log/PID files are all ignored by Git.

For the required wrong-record demo on Laptop 1: `python3 dns/configure_dns.py --record-laptop 1`, then restart DNS. Restore with `python3 dns/configure_dns.py`, then restart again. Full reversible procedures are in [FAILURE_ANALYSIS.md](../docs/FAILURE_ANALYSIS.md).

The team uses two physical Macs and combines machine roles. The assignment's specific requirement asking two other Macs to use the DNS resolver cannot be literally demonstrated with two physical Macs and should be confirmed with faculty.
