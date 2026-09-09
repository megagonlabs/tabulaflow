# Neo4j connection schemes and SSH tunnels

Use the connection URI supplied by the Neo4j deployment. Its scheme selects
routing, encryption, and certificate verification:

| Scheme | Connection | TLS |
|---|---|---|
| `neo4j://` | Routed | No |
| `neo4j+s://` | Routed | Trusted certificate |
| `neo4j+ssc://` | Routed | Self-signed certificate |
| `bolt://` | Direct | No |
| `bolt+s://` | Direct | Trusted certificate |
| `bolt+ssc://` | Direct | Self-signed certificate |

Examples:

```text
bolt://neo4j:password@localhost:7687?database=neo4j
neo4j+s://user:password@host?database=neo4j
```

Do not substitute schemes automatically. A public endpoint where
`neo4j+s://` succeeds but `neo4j://` and `bolt://` fail likely requires TLS.
Testing `bolt+s://` distinguishes a TLS requirement from a routing requirement.

For an SSH-forwarded single server, prefer a direct `bolt` scheme because a
routed `neo4j` connection may receive advertised addresses that are unreachable
through the tunnel. Match the TLS suffix to the server configuration; trusted
TLS may also require the connection hostname to match the server certificate.

Common errors:

- `Unable to retrieve routing information`: routing discovery failed or
  returned unreachable addresses.
- Incomplete Bolt handshake: commonly a TLS mismatch or a non-Bolt endpoint.
- Certificate verification failure: the certificate is untrusted or does not
  match the connection hostname.
