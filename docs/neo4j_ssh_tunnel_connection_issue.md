# Neo4j connection issue with SSH-forwarded Bolt ports

## Summary

Connecting to a Neo4j database through an SSH-forwarded local port can fail even when the database itself is healthy and reachable from the user’s shell.

In this session:

- A Neo4j instance was running remotely on `mdc-gpu002`
- It was exposed remotely on Bolt port `15067`
- An SSH tunnel was created locally:
  - `127.0.0.1:17687 -> mdc-gpu002:15067`
  - `127.0.0.1:17474 -> mdc-gpu002:17474`
- Direct shell-level access through the tunnel worked
- But `connect_data_source` failed for both:
  - `neo4j://neo4j:cypherbench@127.0.0.1:17687`
  - `bolt://neo4j:cypherbench@127.0.0.1:17687`

Observed errors:

- `neo4j://...`: `ServiceUnavailable: Unable to retrieve routing information`
- `bolt://...`: `Couldn't connect to 127.0.0.1:17687 ... Connection to 127.0.0.1:17687 closed with incomplete handshake response`

## Why this happens

There are two distinct issues.

### 1. `neo4j://` expects routing

The `neo4j://` scheme is intended for routed Neo4j connections. The client asks the server for routing/cluster information.

That does not play well with a simple SSH local forward because:

- the forwarded endpoint is synthetic (`localhost:17687`)
- the server may advertise a different host/port than the forwarded one
- a single-instance or forwarded deployment may not provide the routing info the driver expects

Result: `Unable to retrieve routing information`.

### 2. `127.0.0.1` only makes sense in the tunnel creator’s network context

The SSH tunnel was created from the shell on the laptop, so `127.0.0.1:17687` was valid from that shell.

However, the connection tool did not behave as if it were using that exact same localhost endpoint/context. As a result, the Bolt handshake failed even though the tunnel listener existed.

Possible reasons include:

- the connector process runs in a different network namespace / sandbox / container
- `127.0.0.1` inside the connector is not the same `127.0.0.1` as the shell that created the tunnel
- the driver/connector expects a direct Bolt endpoint rather than a forwarded endpoint with mismatched advertised addresses

Result: `incomplete handshake response` / failed Bolt connection.

## Important implication

A database being reachable from `ssh`, `curl`, `cypher-shell`, or a user-started local tunnel does not guarantee that `connect_data_source` can reach the same endpoint.

This is especially true when:

- the destination is only reachable through SSH forwarding
- the host is `127.0.0.1` / `localhost`
- the client library expects Neo4j routing semantics

## Reproduction outline

1. Start a Neo4j instance on a remote machine (example: `mdc-gpu002`) and expose Bolt on a remote port.
2. Create a local SSH tunnel:

   ```bash
   ssh -N -L 17687:localhost:15067 -L 17474:localhost:17474 mdc-gpu002
   ```

3. Verify the local forwarded ports are listening.
4. Try to connect via the application connector using:

   ```text
   neo4j://neo4j:cypherbench@127.0.0.1:17687
   ```

   and then:

   ```text
   bolt://neo4j:cypherbench@127.0.0.1:17687
   ```

5. Observe the routing failure / handshake failure.

## Workarounds

### Short-term workaround

Do not rely on `connect_data_source` for SSH-forwarded Neo4j.

Instead:

- query Neo4j through the SSH session itself (for example with `cypher-shell` or the HTTP transactional endpoint)
- materialize the results into a normal tabular result
- render graphs from those results with `render_graph`

This avoids the connector/network mismatch entirely.

### Better connector behavior

Potential fixes to support this case properly:

1. Prefer `bolt://` over `neo4j://` for single-instance forwarded Neo4j connections.
2. Document that `neo4j://` may fail for SSH-forwarded or non-routed setups.
3. Ensure the connector can access the same localhost namespace as the shell-created tunnel.
4. If the connector runs in isolation, expose a supported way to create the tunnel inside that same environment.
5. Consider supporting an explicit `encrypted=false` / direct Bolt configuration when appropriate.
6. Add better error messages that distinguish:
   - routing discovery failure
   - TCP reachability failure
   - Bolt handshake failure
   - auth failure
7. If the connector uses a Neo4j driver with routing defaults, force direct-driver mode for `bolt://` targets.

## Suggested docs note

When documenting Neo4j connections, add a note like:

> SSH-forwarded Neo4j instances may not work with `connect_data_source`, especially via `neo4j://` URLs, because routing metadata and localhost semantics may not match the connector runtime. For forwarded instances, prefer querying via `cypher-shell`/HTTP inside the SSH session and importing the results.

## Open question to investigate

The main implementation question is:

- Is the connector runtime actually sharing the host network namespace with the shell?

If not, any localhost-based SSH tunnel created in the shell will be unreliable for `connect_data_source` unless the tunnel is established inside the connector’s own runtime.
