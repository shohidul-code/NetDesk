# UI — NetDesk

Frontend design specification for the Phase 7 coding agent. Hand it over together with `RULES.md` and `FRONTEND_AGENT_BRIEF.md`. The source is `docs/PROPOSAL.md` §11 (and §5, §8.1, §8.3). If this file and the proposal disagree, the proposal wins; report the difference.

Stack: React + TypeScript + Vite, React Router, TanStack Query, Tailwind + shadcn/ui, react-hook-form + zod. API types are generated from `/openapi.json` with openapi-typescript (§11.1).

## 1. Principles

1. **Phone first.** Most customers are on a phone on a weak connection. Design at 360px, then widen.
2. **Answer before navigation.** The customer home shows status and amount due without a tap.
3. **Calm utility.** It should feel like a dependable service, not a marketing page.
4. **Two languages.** Bangla and English text must both look right. A full language toggle is P1.
5. **Show where answers come from.** Tool chips and source chips are part of the product, not decoration.
6. **The UI hides, the API enforces.** The UI only hides what a role cannot use (§11).

## 2. Design tokens

### Colour
| Token | Light | Use |
|---|---|---|
| `bg` | `#F7F8FA` | Page background |
| `surface` | `#FFFFFF` | Cards, tables, inputs |
| `border` | `#E3E6EB` | Dividers, input borders |
| `text` | `#16202E` | Body text |
| `text-muted` | `#5B6676` | Secondary text |
| `primary` | `#0F6FDE` | Buttons, links, user chat bubble |
| `primary-hover` | `#0B58B3` | Hover and pressed |
| `success` | `#1B8A4B` | Paid, active, resolved |
| `warning` | `#B26A00` | Unpaid, open, assigned |
| `danger` | `#C2372B` | Suspended, delete, errors |

Status always pairs colour with a word, never colour alone. Contrast is at least 4.5:1 (§11.3).

### Type
- Font stack: `"Inter", "Noto Sans Bengali", system-ui, sans-serif`. §11.3 asks for a Bangla web font and gives Noto Sans Bengali as the example, so use it.
- Sizes: 12 caption, 14 secondary, 16 body, 20 section title, 24 page title.
- Line height 1.5 for body; Bangla needs the extra room.
- Numbers in tables use tabular figures.

### Spacing and shape
- Spacing scale: 4, 8, 12, 16, 24, 32.
- Radius: 8 for inputs and buttons, 12 for cards, 16 for chat bubbles.
- One soft shadow for raised cards.
- Touch targets at least 44px high.

## 3. Layout

| Width | Layout |
|---|---|
| Under 640px | Single column; bottom navigation for customers; top bar with a menu for staff; tables collapse to stacked cards (§11.3) |
| 640px and up | Left sidebar for staff; content max width 1200px; tables as tables |

The menu comes from `me.role` (§11.3).

P0 navigation:
- Customer (bottom bar): Home, Assistant, Complaints.
- Technician: Complaints, Connections (read-only), Assistant.
- Admin: Connections, Bills, Notices, Complaints, Assistant.
- Every role: Profile (shows `/auth/me`, sign out).

## 4. Pages

P0 is exactly 9 pages (§5, Refined plan):

| # | Page | Role |
|---|---|---|
| 1 | Login | All |
| 2 | Claim account | Customer |
| 3 | Customer home (includes the customer's bills) | Customer |
| 4 | Assistant | All |
| 5 | My complaints | Customer |
| 6 | Technician queue | Technician |
| 7 | Admin connections | Admin (technician read-only) |
| 8 | Bills | Admin |
| 9 | Notices | Admin |

**P1, not built in Phase 7:** Packages, Users, Knowledge, owner Dashboard. Swagger covers them meanwhile (§5, Refined plan).

## 5. Components

| Component | Notes |
|---|---|
| Button | Primary, secondary, danger, text. Shows a spinner and disables while its request runs |
| Input, Select, Textarea | Label above, help or error text below, error state with icon |
| Status badge | Word plus colour: Paid, Unpaid, Active, Suspended, Disconnected, Open, Assigned, Resolved |
| Card | Title, body, optional action |
| Data table | Headers, row actions, pagination (`limit`, `offset`); collapses to cards on small screens |
| Filter bar | Area select, status select, search box with a short typing delay |
| Modal / drawer | Create and edit forms; drawer from the bottom on phones |
| Confirm dialog | For delete; names the item being removed |
| Toast | Success and failure messages |
| Empty state | Short explanation plus the next action |
| Skeleton | Placeholder while loading lists and cards |
| Chat bubble | User right in primary; assistant left on surface |
| Tool chip | Small pill under an assistant message, e.g. "Checked your bill" |
| Source chip | Pill per document used (`ref`, title) under an assistant message |
| No-information bubble | A different style for the "no evidence" reply (see Assistant) |

shadcn/ui (Radix) supplies the dialog, menu and focus handling (§11.1).

## 6. Screens

### 1. Login
Centred card, product name, one-line description. Email and password with show/hide. Link to Claim account. Failed login shows "Incorrect email or password" (same message for any failure). 429 shows "Too many attempts. Wait a little and try again."

### 2. Claim account
Fields: customer code, phone, email, password (show/hide). Link back to Login. This claims an existing connection; it does not create one (§6.10, §8.1).
- 404 "no matching connection": "We could not find a connection with this code and phone. Check them or call your operator."
- 409 (email taken or connection already claimed): show the server message beside the form.
- 422: field errors under the inputs.
- 429: "Too many attempts."

### 3. Customer home
1. **Connection card:** package name, speed, area, status badge, customer code.
2. **Bills card:** current bill, due date, status badge, how to pay. Below it, the list of bills by month, newest first: month, amount, status badge, paid date when paid. Total due in large type; when nothing is due: "All paid". Empty: "No bills yet".
3. **Notice banner:** shows the active outage notices for the customer's area (`GET /notices`, scoped by the API).
4. **Latest complaint:** status and date, or a button to report a problem.
5. **Ask the assistant** button.

### 4. Assistant
- Left list (a drawer on phones) of chat sessions: `GET /chat/sessions`. "New chat" creates a session. Delete asks for confirmation. The server keeps the history; opening a session loads its messages.
- Header shows "messages left today".
- Empty state: a greeting and three suggestion chips: "How much do I owe?", "My internet is down", "How do I pay by bKash?".
- The user's message appears at once. A "Thinking…" row shows while the request runs; send is disabled. Streaming is P2.
- Under an assistant reply: tool chips and source chips.
- When the reply says nothing relevant was found, show it in a visibly different style. Do not hide or rephrase it.
- The reply area has `aria-live` so screen readers announce new replies (§11.3).
- Composer fixed at the bottom. Enter sends, Shift+Enter adds a line. Message length 1 to 1000 characters.
- 429 daily limit: "You have used today's messages. Try again tomorrow." Disable the composer.
- 503: "The assistant is temporarily offline." Keep the typed text and show Retry.

### 5. My complaints
List with category, date, status. Form: category select, description (required, with a character count). 403 (complaints are admin-only when the flag is off): show "Complaints are taken by your operator for now."

### 6. Technician queue
Filter by area and status. Each row or card: customer code, area, category, hours open, status. Opening one shows the description and lets staff update the status. 409 invalid status change shows inline. Empty: "No open complaints".

### 7. Connections (admin; technician read-only)
Filter bar and search, with pages. Columns: code, customer, phone, package, area, status, actions. Create and edit in a drawer. Delete asks for confirmation; a 409 shows inline: "Has bills — set Disconnected instead".

### 8. Bills (admin)
Filter by status and period. "Generate bills for a month" shows the result as created and skipped counts (§8.1). "Verify payment" opens a small form with the TrxID; a reused TrxID or an already paid bill shows the 409 message.

### 9. Notices (admin)
List with area and active state. Post a notice for an area; end (edit) a notice. Validation errors under the inputs.

## 7. States every screen needs

| State | Treatment |
|---|---|
| Loading | Skeletons shaped like the content |
| Empty | Message and a next action |
| Error | Friendly message, Retry, and "Details" with the `request_id` |
| No access | "No access" page with a link home |
| Slow network | Buttons show progress; nothing can be submitted twice |

## 8. Errors

Every error body is `{"error": {"code", "message", "details", "request_id"}}` (§8.3). Map `code` to friendly text. Show `request_id` under "Details" so a user can quote it to support (§11.3). Never show raw JSON or a stack trace.

| Status | UI |
|---|---|
| 401 | Clear the session and go back to Login |
| 403 | "No access" page or message |
| 404 | Not-found state in place (also for something outside the user's scope) |
| 409 | Show the server message beside the form (duplicate code, reused TrxID, invalid status change) |
| 422 | Field errors from `details` (`{field, message}` pairs) under the inputs. The API never echoes the submitted value, so keep the user's typed input in the form |
| 429 | Login: "Too many attempts". Chat: daily limit message. Respect `Retry-After` |
| 503 | "The assistant is temporarily offline" |
| 500 or network failure | "Something went wrong, try again" with Retry and `request_id` under "Details" |

## 9. Formats and wording

- Money: `৳1,200`. Month: `Oct 2026`. Date: `12 Oct 2026`. Times in Asia/Dhaka.
- Buttons say what they do: "Verify payment", "Create connection", not "Submit".
- Errors say what to do next.
- Plain words. No "token" or "422" in front of customers.

## 10. Accessibility

- Every input has a visible label.
- Focus is always visible; modals trap focus and close on Escape.
- `aria-live` on the chat reply area.
- Works with keyboard only.
- Status badges use text, not only colour.
- Respects reduced-motion settings.
