# Individual viva preparation

Rakshita: lead the primary/backup DNS, TTL and packet explanations. Lakshya:
lead nginx, TLS and backend isolation explanations. Both must be able to narrate
the complete topology, failures, restoration commands and limitations. Names,
ports and packet numbers must come from the actual live evidence.

| Question | Answer to understand and explain |
|---|---|
| Why two resolvers? | A service failure on one DNS host need not prevent new lookups. Identical records and both client server addresses are necessary. |
| Is backup DNS a web proxy? | No. It supplies an IP address; TCP/TLS/HTTP then go to the selected edge independently. |
| Does listing primary first guarantee it is always used? | No. Native resolver selection and retry policies can adapt. Prove a backup query with logs/capture after flushing. |
| What is DNS TTL? | The lifetime a cache may reuse a record. Direct authoritative/local answers can show the full configured TTL on every query; a forwarding cache shows a decreasing remaining TTL. |
| Why can a new DNS record still send me to the old edge? | My resolver/browser may retain the previous answer until its original TTL, and an existing connection is already attached to that edge. |
| Can lowering TTL at cutover invalidate old caches? | No. Lower it in advance and wait out the previously published lifetime. Flushing affects only the caches actually flushed. |
| How does the automated TTL test differ from the Mac demo? | It uses a real temporary dnsmasq forwarding cache on loopback. Native mDNSResponder/browser caching is a separate live observation. |
| What makes a backend healthy to this nginx? | It has not exceeded passive failure criteria on real requests. Errors/timeouts mark it failed temporarily; a later request after fail_timeout probes recovery. |
| What are max_fails and fail_timeout here? | One failed attempt can quarantine that upstream for a default five-second window. Requests can retry the other server. Recovery is observed through traffic. |
| Are these active health checks? | No. This implementation uses passive checks and bounded diagnostic requests; it does not claim nginx Plus active health checking. |
| How can a request survive stopping A? | The edge's client connection remains healthy; a separate upstream attempt to A fails, and nginx retries the safe GET against B. |
| Why should retries be limited? | Unbounded retries increase latency/load. Retrying non-idempotent requests can duplicate side effects; our simple demonstration uses GET/HEAD. |
| What happens when both backends stop? | DNS/TCP/TLS can all succeed, then the edge returns an explicit HTTP 502 upstream-unavailable response. |
| Why not only allow the edge IP in PF? | A client co-located on that edge has the same source IP. Both-host outbound UID checks distinguish its ordinary client sockets from nginx worker sockets. |
| What is still permitted by the UID rule? | Every process running under the authorized worker account. Reserve that identity for nginx; root can alter the policy and is outside this threat model. |
| Why is loopback important? | Some client/server paths share a Mac and may use lo0. Skipping loopback can bypass isolation; capture and test local paths too. |
| Why restart backends after enabling PF? | Existing stateful connections may remain allowed without evaluating new rules. Backend restart closes old sessions without globally flushing unrelated PF states. |
| How is rollback safe? | Only the project anchor is removed and only its own PF enable-reference token is released. Existing root rules and other PF users remain untouched. |
| How does the standby prove migration? | Same names, ports, upstream behavior and trusted CA, but a distinct key/certificate and X-Edge identity. Change both DNS servers, observe TTL, then normal system-resolved HTTPS reaches standby. |
| Why not copy the primary private key? | Each edge can keep its own key and CSR. The project CA signs both names; clients trust the public CA. Only public material needs to move. |
| Is controlled DNS migration automatic HA? | No. The active edge remains a failure point until an operator updates DNS and clients refresh. Automated monitoring and a DNS/VIP failover controller would be additional work. |
| What if an entire laptop fails? | Several co-located roles disappear at once. The surviving services help, but cached DNS and loss of a resolver/edge still affect recovery. |
| DNS TTL versus HTTP max-age? | They cache different objects: an address record versus an HTTP representation. The same number of seconds does not make them the same cache. |
| Why an ETag and 304? | A validator lets the server confirm unchanged content without resending the body. Both backends intentionally share the representation and ETag. |
| What can Wireshark see? | DNS and TCP metadata; visible portions of TLS handshake; encrypted client application payload; plaintext HTTP on the backend hop. TLS 1.3 encrypts Certificate after ServerHello. |
| What evidence is complete today? | Read TEST_RESULTS.md. Local process tests and actual syntax checks are verified; two-Mac/admin/packet demonstrations must be recorded live before claiming completion. |

For each extension, rehearse: requirement -> relevant config -> observable
failure -> recovery -> evidence -> remaining limitation. Then swap topics.
During diagnosis identify the last successful layer before changing anything.
