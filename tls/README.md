# TLS certificate and client trust

On Laptop 2, run `./tls/generate_certificate.sh` after filling `network.env`. The default preserves the permitted OpenSSL self-signed server-certificate approach. It generates `tls/certs/server.crt`, `server.key` and an OpenSSL config. SANs include both `APP_DOMAIN` and `API_DOMAIN`; it is not a Common-Name-only certificate. It includes serverAuth and 90-day validity. Existing material is never silently replaced; private files have restrictive permissions.

The optional `./tls/generate_certificate.sh --local-ca` creates `ca.crt`/`ca.key` and a CA-signed server certificate with the same SANs. The assignment's local-CA route requires faculty approval; confirm that route before selecting it. The default self-signed route does not require choosing a separate local CA.

Copy only the public `server.crt` to Laptop 1; for the CA route also copy `ca.crt`. Run `./tls/trust_certificate.sh` on both clients. It prints identity/fingerprint and invokes the macOS System Keychain trust procedure. The helper trusts `ca.crt` if present, otherwise the self-signed `server.crt`. Verify that both clients received the same public anchor.

Official HTTPS tests use `--cacert` with that public anchor and still validate chain/signature, expiry and hostname. They never use an insecure validation-bypass flag. Also show browser access without warnings, which demonstrates actual Keychain trust. nginx holds the matching server key and terminates TLS; backend connections use HTTP.

All generated contents of `certs/` are ignored except `.gitkeep`. Do not publish private keys or copy them to Laptop 1. To rotate, explicitly move old material outside `certs/`, regenerate on Laptop 2 and update both clients' trust. [Removal procedure](remove_certificate.md).
