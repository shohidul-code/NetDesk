# PRD — NetDesk

Product requirements. Background and pitch are in `PROJECT_IDEA.md`; this file states what must be true when the product is done.

## 1. Summary

NetDesk is an AI support and billing desk for neighbourhood broadband operators in Bangladesh. Customers get answers about outages, bills and router problems from the operator's live data and documents. Staff manage connections, bills and complaints.

## 2. Goals

| # | Goal | How we know |
|---|---|---|
| G1 | Cut repeat phone calls | The three most common questions (bill, outage, router light) are answered correctly by the assistant |
| G2 | No missed bills | The owner can list every unpaid bill in one step |
| G3 | Tracked complaints | Every complaint has an owner, a status and timestamps |
| G4 | Trustworthy answers | Account facts come only from the database; policy answers only from documents; otherwise the assistant says it does not know |

## 3. Non-goals

- Taking real payments (bKash/Nagad integration)
- Controlling network equipment or cutting lines automatically
- Sending SMS
- Multi-operator (multi-tenant) accounts
- A native mobile app

## 4. Users

| Persona | Description | Main need |
|---|---|---|
| **Rahim, customer** | Home user in Mirpur 10, on a phone, writes Banglish | Know why the net is down and what he owes |
| **Sumon, technician** | Covers two areas by motorbike | A clear list of jobs by area |
| **Mr. Karim, owner** | Runs a 600-connection operator with two staff | See collections and stop the phone ringing |

## 5. Functional requirements

Priority: **M** must (graded), **S** should (real-product depth).

### Accounts and access
| ID | Requirement | P |
|---|---|---|
| FR-1 | A person can register with name, email, phone and password, and becomes a customer | M |
| FR-2 | A person can log in and receives a token that expires | M |
| FR-3 | A logged-in person can view their own profile and role | M |
| FR-4 | Three roles exist: admin, technician, customer | M |
| FR-5 | Wrong email and wrong password give the same login error | M |
| FR-6 | An admin can change a user's role | S |

### Packages
| ID | Requirement | P |
|---|---|---|
| FR-10 | Any logged-in user can list and view packages | M |
| FR-11 | Only an admin can create, edit or delete a package | M |
| FR-12 | A package in use by a connection cannot be deleted | M |

### Connections
| ID | Requirement | P |
|---|---|---|
| FR-20 | Only an admin can create, edit or delete a connection | M |
| FR-21 | Staff can list connections filtered by area and status, and search by name, phone or customer code | M |
| FR-22 | A customer can view only their own connection | M |
| FR-23 | Customer codes are unique | M |
| FR-24 | A connection with bills is disconnected, not deleted | S |
| FR-25 | Lists are paginated and sortable | S |

### Bills
| ID | Requirement | P |
|---|---|---|
| FR-30 | An admin can create a bill for a connection and month; one bill per connection per month | M |
| FR-31 | An admin can mark a bill paid with a method | M |
| FR-32 | A customer sees only their own bills | M |
| FR-33 | An admin can generate the month's bills for all active connections in one action | S |
| FR-34 | A paid bill records transaction ID and who received it | S |
| FR-35 | A connection with two or more unpaid months can be suspended; payment reactivates it | S |

### Complaints
| ID | Requirement | P |
|---|---|---|
| FR-40 | A customer can file a complaint on their own connection with category and description | M |
| FR-41 | Staff can list complaints filtered by area and status | M |
| FR-42 | Staff can assign a complaint and mark it resolved | M |
| FR-43 | A customer sees only their own complaints | M |
| FR-44 | Assigned and resolved times are recorded | S |
| FR-45 | An admin can post an area outage notice with an expected fix time | S |

### Assistant
| ID | Requirement | P |
|---|---|---|
| FR-50 | A logged-in user can chat; earlier messages are understood | M |
| FR-51 | The assistant reports the customer's unpaid bills from the database | M |
| FR-52 | The assistant reports open complaints (and any outage notice) for an area from the database | M |
| FR-53 | The assistant answers how-to and policy questions from the operator's documents and names the source | M |
| FR-54 | When no document matches, the assistant says so | M |
| FR-55 | A customer can never obtain another customer's data through chat | M |
| FR-56 | The assistant declines topics outside the operator's business | M |
| FR-57 | The reply lists which tools ran and which sources were used | S |

### Staff integration (MCP)
| ID | Requirement | P |
|---|---|---|
| FR-60 | An MCP client can call two tools: bill status by customer code, open complaints by area | M |
| FR-61 | An MCP client can read the active package list as a resource | M |
| FR-62 | An MCP client can use a due-bill reminder prompt | M |
| FR-63 | The MCP server works over HTTP and over stdio | M |

### Owner view
| ID | Requirement | P |
|---|---|---|
| FR-70 | The owner sees active connections, collected and due this month, and open complaints per area | S |

## 6. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Errors never expose stack traces or database messages |
| NFR-2 | Passwords are stored hashed; secrets live only in environment settings |
| NFR-3 | The app refuses to start when a required secret is missing |
| NFR-4 | A fresh clone runs with `docker compose up` by following the README |
| NFR-5 | The frontend is usable at 360px width and renders Bangla correctly |
| NFR-6 | A typical page loads its data in about a second on local Docker; a chat reply shows a waiting indicator |
| NFR-7 | The API is browsable at `/docs` on the live link |

## 7. Acceptance scenarios

1. Rahim logs in, asks "amar bill koto baki?", and gets his exact unpaid months and total.
2. Rahim asks about another customer's code; the assistant refuses.
3. Rahim asks about a red router light; the answer cites the troubleshooting guide.
4. Rahim asks "Do you sell Starlink?"; the assistant says the documents don't cover it.
5. Sumon filters complaints to Mirpur 10 and resolves one.
6. Mr. Karim creates a connection with a duplicate code and sees a conflict message.
7. Rahim calls an admin-only endpoint and gets a forbidden error.
8. From an MCP client, the due-bill reminder prompt produces a message for a given customer code.

## 8. Release checklist

- All **M** requirements pass
- Seed data and documents loaded on the live deployment
- README holds the repo, video and live Swagger links
- Rubric checklist in `BUILD_PLAN.md` fully ticked
