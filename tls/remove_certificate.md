# Remove project certificate trust after evaluation

Keep the public certificate until you identify its exact trust entry:

```sh
openssl x509 -in tls/certs/server.crt -noout -subject -fingerprint -sha256
```

For the optional CA route, inspect `tls/certs/ca.crt` instead. On each client, open Keychain Access, choose the System keychain, locate the project app certificate or team course CA, and compare its fingerprint with the actual public file. Delete only that matching project certificate/trust entry. Leave unrelated system certificates alone.

Close/reopen the browser to refresh trust behavior. If a curl command explicitly supplies the public file with `--cacert`, that command independently trusts the file; it is not a check that Keychain removal failed. Stop nginx and backends, restore original client DNS settings, and retain genuine evaluation evidence.
