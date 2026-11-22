# PRD — NetDesk

Product requirements. Background and pitch are in `PROJECT_IDEA.md`; this file states what must be true when the product is done. Source of truth: `PROPOSAL.md`. Section numbers (§) point there.

## 1. Summary

NetDesk is a Bangla-first AI support desk that works next to the ISP's existing billing tool (§3 Positioning). It is not a billing desk and not a RADIUS or router-control product. Customers ask about bills and outages and get answers from the operator's own records and help articles. Problems the assistant cannot solve become complaints for technicians.

## 2. Goals

| # | Goal | How we know |
|---|---|---|
| G1 | Cut repeat phone calls | The common questions (bill, outage, router light) are answered correctly; see the metrics in §5 |
| G2 | No missed bills | The admin can list every unpaid bill with `GET /bills?status=unpaid` |
| G3 | Tracked complaints | Every complaint has a status and an optional assignee |
| G4 | Trustworthy answers | Account facts come only from tools (database); help and policy facts only from cited documents; otherwise the assistant says it has no information |

## 3. Non-goals (P1 and P2 stay out of P0, §5)

- Taking real payments (bKash/Nagad gateway), SMS reminders, Messenger or WhatsApp channel (P2)
- Controlling routers or cutting lines automatically (P2)
- Multi-tenancy (P2). Build it before charging a 4th customer (Refined plan)
- A native mobile app; streaming replies; refresh tokens

## 4. Users and roles

| Persona | Description | Main need |
|---|---|---|
| Rahim, customer | Home user on a phone, writes Banglish | Know why the net is down and what he owes |
| Sumon, technician | Covers areas by motorbike | A clear queue of complaints |
| Mr. Karim, admin (owner) | Runs an ISP with 200–2,000 connections (assumption) | Fewer calls; see dues and complaints |

| Role | Can do | Cannot do |
|---|---|---|
| Admin | All CRUD, bill generation, payment verification, notices, create technicians, MCP | — |
| Technician | Read connections and bills, update complaints, staff chat tools, MCP | Write connections, packages, bills or users |
| Customer | Read own connection and bills, chat, create complaints for own connection | See other customers; call staff tools; use MCP |

Full access model: §7.3. Out of scope → 404; role not allowed → 403.

## 5. Success metrics (all targets are hypotheses, §3)

| Outcome | Metric | Pilot target (hypothesis) |
|---|---|---|
| Fewer repetitive calls | Support calls per 100 connections per month | −20% against a one-week baseline |
| Self-service | Chat sessions with no complaint opened within 24 h | ≥ 30% |
| Grounded answers | Eval: correct tool use; correct "no information" replies | ≥ 90% each |
| Faster outage notices | Minutes from first complaint to posted notice | Measure the baseline first |

## 6. Functional requirements

Priority: **P0** graded or needed for one end-to-end demo; **P1** quality extras, built only after P0 (§5).

### Accounts and access
| ID | Requirement | P |
|---|---|---|
| FR-1 | Claim-style register: a person gives customer code, phone, email and password and becomes a customer linked to that connection. No matching connection → 404. Email taken or connection already claimed → 409 | P0 |
| FR-2 | A person can log in and gets a token that expires after 30 minutes | P0 |
| FR-3 | A logged-in person can view their own profile and role. An inactive user or expired token → 401 | P0 |
| FR-4 | Three roles exist: admin, technician, customer | P0 |
| FR-5 | Unknown email and wrong password give the same 401 | P0 |
| FR-6 | An admin creates technician accounts and can deactivate users. Users are never deleted, and the last admin cannot be deactivated (409). There are no free role changes | P0 |

### Packages
| ID | Requirement | P |
|---|---|---|
| FR-10 | Any logged-in user can list packages; customers see active ones | P0 |
| FR-11 | Only an admin can create, edit or delete a package. A duplicate name or a package in use returns 409 | P0 |

### Connections
| ID | Requirement | P |
|---|---|---|
| FR-20 | Only an admin can create, edit or delete a connection | P0 |
| FR-21 | Staff can filter connections by area, status and package, and search by `q` | P0 |
| FR-22 | A customer can view only their own connection | P0 |
| FR-23 | Customer codes are unique (409). A connection with bills cannot be deleted (409); the admin sets `disconnected` | P0 |
| FR-25 | Lists are paginated (limit/offset, total count, max 100) and sortable | P0 |
| FR-26 | CSV import of connections | P1 |

### Bills
| ID | Requirement | P |
|---|---|---|
| FR-30 | An admin can create a bill for a connection and month (one per connection per month) and mark it paid with a method | P0 |
| FR-32 | A customer sees only their own bills | P0 |
| FR-33 | An admin generates the month's bills for all active connections; running it twice is safe (created and skipped counts) | P0 |
| FR-34 | An admin verifies a payment by TrxID. A reused TrxID returns 409. A paid bill records who verified it | P0 |
| FR-35 | "Suspend after 2 unpaid months", run from an admin endpoint | P1 |
| FR-36 | A customer submits a payment claim with a TrxID; the admin approves it | P1 |

### Complaints and notices
| ID | Requirement | P |
|---|---|---|
| FR-40 | A customer can file a complaint on their own connection with category and description | P0 |
| FR-41 | Staff can list complaints by area and status and change status (`open → in_progress → resolved → closed`, or reopen `resolved → in_progress`; any other change → 409). Only an admin assigns them (§7.3) | P0 |
| FR-43 | A customer sees only their own complaints | P0 |
| FR-44 | Assigned and resolved times are recorded | P1 |
| FR-45 | An admin can post and end an area outage notice; customers read notices for their own area | P0 |
| FR-46 | `ALLOW_CUSTOMER_COMPLAINTS=false` makes complaint creation admin-only (customer gets 403). Technicians never create complaints; they update status. This absorbs the instructor's answer to §4 conflict 1 | P0 |

### Assistant
| ID | Requirement | P |
|---|---|---|
| FR-50 | A logged-in user can chat in stored sessions. Sessions and messages are saved; only the owner can read or delete them. Delete is soft: the session is hidden from the owner and its messages stay as the audit trail. The last 12 messages are sent to the model (§9.4) | P0 |
| FR-51 | Customer: `get_my_bill_status` reports their bills and total due. Staff: `lookup_customer_bills` by customer code | P0 |
| FR-52 | Customer: `get_my_area_status` reports notices and open complaints in their area. Staff: `get_area_service_status` by area code | P0 |
| FR-53 | The assistant answers how-to and policy questions from help articles and cites the source | P0 |
| FR-54 | When no article is close enough (NO_EVIDENCE), the assistant says it has no information | P0 |
| FR-55 | A customer can never obtain another customer's data through chat. Off-topic requests are declined | P0 |
| FR-57 | Each reply returns `message_id`, `content`, `tools_used`, `sources` and `usage` (§8.2) | P0 |
| FR-58 | Daily chat caps per user and in total: `CHAT_DAILY_LIMIT_CUSTOMER`, `CHAT_DAILY_LIMIT_STAFF`, `CHAT_DAILY_LIMIT_GLOBAL` (defaults 30, 100, 1,500; §9.8). Over the cap → 429 | P0 |
| FR-59 | `CHAT_ENABLED=false` turns chat off with a 503. A provider failure also returns 503 | P0 |

### Staff integration (MCP), staff-only (§9.7)
| ID | Requirement | P |
|---|---|---|
| FR-60 | An MCP client can call two tools: `lookup_customer_bills` and `get_area_service_status` | P0 |
| FR-61 | An MCP client can read the active packages (resource) and render the `due_bill_reminder` prompt. It sends nothing | P0 |
| FR-63 | HTTP at `/mcp` needs a staff JWT (no token → 401, customer → 403, unknown host → 421). Stdio acts as `MCP_STDIO_USER_EMAIL`, which must be an active staff user | P0 |

### Owner view
| ID | Requirement | P |
|---|---|---|
| FR-70 | Dashboard: dues by area, open complaints by area, chats without a complaint. Swagger (`/bills/summary`) covers dues until then | P1 |

## 7. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | One error envelope (§8.3). A 500 shows no traceback; a 422 never echoes submitted input |
| NFR-2 | Passwords are Argon2id hashed; secrets are `SecretStr` from environment settings |
| NFR-3 | The app refuses to start without `DATABASE_URL` or `JWT_SECRET_KEY` |
| NFR-4 | A fresh clone runs with `docker compose up` by following the README |
| NFR-5 | Customer pages are mobile-first and render Bangla (§11.3) |
| NFR-6 | Chat p95 ≤ 8 s excluding cold starts is a target, not yet measured (§9.9). Measure list endpoints in Phase 8 |
| NFR-7 | The API is browsable at `/docs` on the live link, with the free-tier cold-start note beside it |
| NFR-8 | Rate limits: login 5/min and register 3/min per IP; chat 6/min per user (§9.8) |
| NFR-9 | All seed and demo data is synthetic |

## 8. Pricing hypotheses (§14.3; test with owners, not facts)

| Offer | Connections | Monthly | One-time setup |
|---|---|---|---|
| Add-on (keeps their billing tool) | Up to 500 | ৳800 | ৳3,000 |
| Add-on | 501–1,500 | ৳1,800 | ৳3,000 |
| Add-on | 1,501–3,000 | ৳3,000 | ৳5,000 |
| Standalone (billing-lite + AI desk) | Up to 500 | ৳1,800 | ৳5,000 |
| Standalone | 501–1,500 | ৳3,500 | ৳7,500 |

Run at most 3 free pilots. Build multi-tenancy before charging a 4th customer. Make no profit claim.

## 9. Acceptance scenarios

1. Rahim claims his account with his customer code and phone, then logs in.
2. Rahim asks "amar bill koto baki?" and gets his exact unpaid months and total; `tools_used` shows `get_my_bill_status`.
3. Rahim asks for another customer's bill; the assistant refuses.
4. Rahim asks about a red router light; the answer cites the troubleshooting article.
5. Rahim asks "Do you sell Starlink?"; the assistant says it has no information.
6. Sumon filters complaints by area and resolves one.
7. Mr. Karim creates a duplicate customer code (409) and verifies one TrxID on two bills (second gets 409).
8. Rahim calls an admin-only endpoint and gets 403.
9. From an MCP client with a staff token, `due_bill_reminder` produces a message for a customer code; a customer token gets 403.

## 10. Release checklist

- All P0 requirements pass; the access-control tests are green.
- `docs/EVAL_RESULTS.md` is dated, with zero permission leaks and zero successful injections.
- Seed data and articles are loaded on the live deployment; the README has the three links. Full list: PROPOSAL §18.
