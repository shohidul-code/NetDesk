# UI — NetDesk

Frontend design specification. AI assistance is allowed for the frontend, so this file is written to be handed to a coding agent together with `RULES.md` and `FRONTEND_AGENT_BRIEF.md`.

## 1. Principles

1. **Phone first.** Most customers are on a phone on a weak connection. Design at 360px, then widen.
2. **Answer before navigation.** The customer home shows status and amount due without a tap.
3. **Calm utility.** It should feel like a dependable service, not a marketing page.
4. **Two languages.** Bangla and English text must both look right.
5. **Show where answers come from.** Tool badges and sources are part of the product, not decoration.

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

Status always pairs colour with a word or icon, never colour alone. Text on coloured backgrounds must meet WCAG AA contrast.

### Type
- Font stack: `"Inter", "Hind Siliguri", system-ui, sans-serif` (Hind Siliguri covers Bangla).
- Sizes: 12 caption, 14 secondary, 16 body, 20 section title, 24 page title.
- Line height 1.5 for body; Bangla needs the extra room.
- Numbers in tables use tabular figures.

### Spacing and shape
- Spacing scale: 4, 8, 12, 16, 24, 32.
- Radius: 8 for inputs and buttons, 12 for cards, 16 for chat bubbles.
- One soft shadow for raised cards; no heavy shadows.
- Touch targets at least 44px high.

## 3. Layout

| Width | Layout |
|---|---|
| Under 768px | Single column; bottom tab bar for customers; top bar with a menu for staff; tables become stacked cards |
| 768px and up | Left sidebar for staff; content max width 1200px; tables as tables |

Customer tabs: Home, Bills, Complaints, Assistant.
Staff sidebar: Overview (admin), Connections (admin), Packages (admin), Bills (admin), Complaints, Assistant (admin).

## 4. Components

| Component | Notes |
|---|---|
| Button | Primary, secondary, danger, text. Shows a spinner and disables while its request runs |
| Input, Select, Textarea | Label above, help or error text below, error state with icon |
| Status badge | Word plus colour: Paid, Unpaid, Active, Suspended, Disconnected, Open, Assigned, Resolved |
| Card | Title, body, optional action |
| Data table | Sortable headers, row actions, pagination; collapses to cards on small screens |
| Filter bar | Area select, status select, search box with a short typing delay |
| Modal / drawer | Create and edit forms; drawer from the bottom on phones |
| Confirm dialog | For delete and disconnect; names the item being removed |
| Toast | Success and failure messages; disappears after a few seconds |
| Empty state | Short explanation plus the next action |
| Skeleton | Placeholder while loading lists and cards |
| Chat bubble | User right in primary; assistant left on surface |
| Tool badge | Small pill under an assistant message, e.g. "Checked your bill" |
| Sources list | Collapsible list of document names under an assistant message |

## 5. Screens

### Login / Register
Centred card, product name, one-line description. Register has name, email, phone, password with show/hide. Link between the two. One generic error for a failed login.

### Customer home
1. **Connection card:** package name, speed, area, status badge, customer code.
2. **Due card:** total due in large type, count of unpaid months, link to Bills. When nothing is due: "All paid".
3. **Notice banner** (only when the area has an active outage notice): message and expected fix time.
4. **Latest complaint:** status and date, or a button to report a problem.
5. **Ask the assistant** button.

### My bills
List by month, newest first: month, amount, status badge, paid date and method when paid.

### My complaints / New complaint
List with category, date, status. Form: category select, description (required, with a character count).

### Assistant
- Header with "New chat".
- Empty state: a greeting and three suggestion chips: "How much do I owe?", "My internet is down", "How do I pay by bKash?".
- Messages scroll; newest at the bottom; the view follows new messages.
- Under assistant messages: tool badges and collapsible sources.
- Composer fixed at the bottom: multi-line input, send button. Enter sends, Shift+Enter adds a line.
- While waiting: typing indicator, send disabled.
- On failure: an inline error with Retry; the typed text is kept.

### Complaints board (technician and admin)
Filter bar by area and status. Each row or card: customer code, area, category, hours open, status, technician. Opening one shows the description and actions: Assign to me, Mark resolved; admins can assign to any technician.

### Connections (admin)
Filter bar and search. Columns: code, customer, phone, package, area, status, connected on, actions. "New connection" opens the form: customer, package, code, area, address, date.

### Packages (admin)
Cards or table: name, speed, price, active. Create, edit, deactivate, delete.

### Bills (admin)
Filter by status and month. "Generate this month's bills" button with a result summary. "Mark paid" opens a small form: method, transaction ID.

### Admin overview
Four number cards: active connections, collected this month, due this month, open complaints. A small table of open complaints per area.

## 6. States every screen needs

| State | Treatment |
|---|---|
| Loading | Skeletons shaped like the content |
| Empty | Message and a next action |
| Error | Message and Retry |
| No permission | Short explanation and a link home |
| Slow network | Buttons show progress; nothing can be submitted twice |

## 7. Formats and wording

- Money: `৳1,200`. Month: `Oct 2026`. Date: `12 Oct 2026`. Times in Asia/Dhaka.
- Buttons say what they do: "Mark paid", "Create connection", not "Submit".
- Errors say what to do next: "This customer code is already used. Try another."
- Plain words. No technical terms such as "token" or "422" in front of customers.

## 8. Accessibility

- Every input has a visible label.
- Focus is always visible; modals trap focus and close on Escape.
- New assistant messages are announced to screen readers.
- Works with keyboard only.
- Respects reduced-motion settings.
