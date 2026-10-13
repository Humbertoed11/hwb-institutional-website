# Solution: Host Connection Reset on http://mop.test:5000 (BUG-122)

## Problem Description
Visiting `http://mop.test:5000/` or executing `curl http://mop.test:5000/` from the host results in `curl: (56) Recv failure: Connection reset by peer`. The port is open on `127.0.0.1:5000`, but incoming TCP connections are dropped immediately upon sending the HTTP GET request.

## Root Cause
Docker Desktop's virtual port proxy between the WSL2 subsystem and the container bridge loses socket mapping to container `172.19.0.5:5000` after prolonged background tasks or data-heavy sync scripts (e.g. `daycare_registry_sync.py --force`) are executed inside the web container. While the internal Flask application remains healthy, the host proxy resets external connections.

## Resolution
1. Do not run heavy background scrapers or database batch jobs inside the web application container (`hwb_web_app`). Always use the dedicated worker (`hwb_agent_worker`).
2. Execute the standardized container reload command:
   ```bash
   docker restart hwb_web_app
   ```
3. Verify that `curl -I http://mop.test:5000/` returns `HTTP/1.1 200 OK`.
