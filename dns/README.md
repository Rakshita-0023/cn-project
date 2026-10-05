# Codexers DNS on Laptop 1 / Person A

The recorded Type 2 deployment used dnsmasq at `10.7.18.118:53`. Both `app.codexers.test` and `api.codexers.test` point to nginx at `10.7.31.46`, with local TTL 30. These are recorded LAN addresses; the renderer still reads the current values from `network.env`.

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

For the optional reference wrong-record scenario on Laptop 1: `python3 dns/configure_dns.py --record-laptop 1`, then restart DNS. Restore with `python3 dns/configure_dns.py`, then restart again. [FAILURE_ANALYSIS.md](../docs/FAILURE_ANALYSIS.md) separates these reference procedures from the live submission's Backend A stop demonstration.

## Managed Mac / MDM DNS Override

Use this troubleshooting step **only if macOS/MDM overrides normal client DNS**. Keep `set_client_dns.sh` as the primary workflow.

During the real deployment, the network service queried through `networksetup` showed `10.7.18.118`, but `scutil --dns` still showed institutional/public resolvers. The working solution was a domain-specific resolver for `codexers.test`:

```sh
sudo mkdir -p /etc/resolver

printf "nameserver 10.7.18.118\nport 53\n" | \
sudo tee /etc/resolver/codexers.test

sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

If this path already contains an unrelated resolver configuration, preserve its original contents outside Git before changing it and restore them afterwards. If it already contains this working project entry, keep it. Use the current `DNS_IP` instead of the recorded address if redeploying on another LAN.

Verification:

```sh
scutil --dns
dscacheutil -q host -a name app.codexers.test
```

Expected host lookup for the recorded deployment:

```text
name: app.codexers.test
ip_address: 10.7.31.46
```

This creates a domain-specific resolver for `codexers.test` while leaving other DNS traffic under the normal macOS/MDM resolver setup. It is a client resolver-selection fix, not another DNS server. The system resolver uses the best matching domain configuration, as described by macOS `man 5 resolver`.

On macOS, dig does not use this domain-specific routing. Verify the private DNS server separately with `dig @10.7.18.118 app.codexers.test`; use `dscacheutil` and the real domain-based HTTPS request to verify application resolution. Public comparison uses `dig @8.8.8.8 app.codexers.test`, which returned NXDOMAIN during deployment.

### Cleanup

Remove only the project entry you created; if you preserved a pre-existing entry, restore that original instead:

```sh
sudo rm -f /etc/resolver/codexers.test

sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

Also run `./dns/restore_client_dns.sh` if the normal setup script changed network-service DNS. Its backup restores the original service settings, but does not remove `/etc/resolver/codexers.test`.

This project uses Type 2 infrastructure: two physical macOS laptops with combined roles, as supported by the Phase 1 submission form.
