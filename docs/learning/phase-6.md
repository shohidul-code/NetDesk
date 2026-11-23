# Phase 6 — MCP: viva notes

## What was built and why

- An MCP server (official `mcp` SDK, pinned to 2.3.0, class `MCPServer`) gives AI clients
  such as MCP Inspector or Claude Desktop four read-only capabilities for staff:
  - the tools `lookup_customer_bills` and `get_area_service_status`;
  - the resource `netdesk://packages/active`;
  - the prompt `due_bill_reminder`, which only returns text and sends nothing.
- Every capability calls the same service functions as REST and the chat tools, so an
  access rule exists once. MCP adds transport, not business logic.
- **Streamable HTTP at `/mcp`:**
  - a pure ASGI middleware applies the REST auth rules: Bearer JWT, then the user and role
    from the database, then active and staff. It answers 401 or 403 in our error envelope;
  - the FastAPI lifespan starts the MCP session manager, because a mounted sub-app's own
    lifespan never runs;
  - only hosts in `MCP_ALLOWED_HOSTS` get through; others get 421 (DNS-rebinding
    protection).
- **stdio (`uv run netdesk-mcp`):** no token exists on stdio, so the caller is fixed at
  startup. `MCP_STDIO_USER_EMAIL` must be an active staff user, or the process exits 1
  before serving. Logs go to stderr, because stdout carries the protocol.
- **Defence in depth:** each tool also checks for a staff scope, so a future transport
  that forgot the middleware still could not run a tool.
- **Errors:** our own errors become the SDK's `ToolError`, whose message reaches the
  client ("Connection not found."). Anything else becomes a generic error, so no
  traceback or SQL leaves the server.

## Five locations to explain

- `app/mcp/server.py` (`_staff_scope`): where the server refuses non-staff, whatever the
  transport.
- `app/mcp/server.py` (`_as_tool_errors`): which errors the client may see.
- `app/mcp/auth.py` (`StaffJWTMiddleware`): the same rules as `get_current_user`, in ASGI
  form, because an MCP request is not a FastAPI route.
- `app/main.py` (`create_app`):
  - `stateless_http=True`;
  - `transport_security` read from env;
  - the lifespan that runs `session_manager.run()`;
  - an exact `/mcp` route instead of a mount.
- `app/mcp/stdio.py` (`resolve_staff`): fixing the identity at startup.

## Likely viva questions

1. **How does a tool know who is calling?** The middleware (HTTP) or the startup code
   (stdio) puts the user's `Scope` in a context variable, and the tools read it. Stateless
   mode matters here. In stateful mode, a session's server task is created once, at the
   first request, and copies that request's context, so a later request on the same
   session could run with the first caller's identity. In stateless mode every request
   runs its own server task inside its own checked context.
2. **Why not use FastAPI `Depends` for MCP auth?** The MCP app is a separate ASGI app, not
   a FastAPI route, so dependencies never run for it. A rubric test pins `/mcp` as the
   only route outside FastAPI auth and checks that it is wrapped by the middleware.
3. **What is the 421 for?** DNS rebinding: a malicious web page can make a browser send
   requests to `localhost` under an attacker's hostname. The server accepts only the Host
   headers it was configured for. On Render, `MCP_ALLOWED_HOSTS` must include the Render
   host, or every request gets 421.
4. **How is it tested?**
   - in-process: each capability returns what the service returns, refusals, and the
     error messages;
   - over HTTP: 401, 403 and 421 checks, plus one real uvicorn subprocess with the SDK
     client, so the lifespan really runs;
   - over stdio: the installed `netdesk-mcp` script under the SDK stdio client, with a
     user committed for the subprocess and deleted afterwards.
5. **Why did the project become an installable package?** `[project.scripts]` only
   creates `netdesk-mcp` when uv installs the project. `uv_build` is a build-time tool;
   the Docker image still runs `--no-install-project`.

## Rubric rows this phase moves (PROPOSAL §4)

- **B9 MCP (8):** 2 tools, 1 resource and 1 prompt over Streamable HTTP and stdio, staff
  JWT, host allowlist, the same services as REST, SDK client tests over both transports,
  and the smoke check. Remaining: the MCP Inspector clip (owner, HUMAN_TODO §5b).
