# NetDesk — Project Idea and Product Plan

The product side of the project: what it is, who it is for, what it does and how it earns money. The technical side (architecture, tables, endpoints, build steps) is in `BUILD_PLAN.md`.

Numbers marked *(assumption)* are starting guesses. Replace them after talking to a real operator.

---

## 1. One-line pitch

**NetDesk is an AI support and billing desk for neighbourhood broadband operators in Bangladesh.** It answers customers' questions from the operator's real data and documents, so the office phone stops ringing for the same three questions.

---

## 2. The problem

Most homes in Dhaka and district towns get internet from a small local operator, not a national company. A typical office is two or three people with a phone, a paper register or an Excel file, and a bKash number.

| Who | Pain today |
|---|---|
| Customer | Net goes down, calls the office, line is busy. Does not know if it is their router or an area fault. Does not remember if this month's bill is paid. |
| Office staff | The same questions all day: "net nai keno?", "bill koto?", "bKash number ki?". During a fibre cut, fifty people call about one fault. |
| Technician | Gets complaints by phone call or Messenger, with no list, no area view and no record of what was fixed. |
| Owner | Does not know at a glance who has not paid, how much is due this month, or which area complains most. |

---

## 3. Who buys it

**Target customer:** owners of area broadband operators with about 200 to 2,000 connections *(assumption)*.

**Why this buyer:**
- They already collect money every month, so a small monthly fee is a normal cost.
- They lose customers to competitors mainly over poor support, so better support protects income.
- Their current tools are paper, Excel, a Facebook page and phone calls.

**Who uses it day to day:** the owner (admin), line technicians, and the operator's customers.

---

## 4. What it does

### For customers
- Ask the assistant in Bangla or English, any time.
- See their package, connection status, bills by month and total due.
- File a complaint and follow its status.
- Get told about a known area outage before they need to call.

### For technicians
- A list of open complaints, filtered by area.
- Take a complaint, mark it resolved, with times recorded.

### For the owner
- Manage packages, connections, bills and complaints in one place.
- Generate the month's bills in one action; mark payments with method and transaction ID.
- Post an area outage notice.
- See totals: active connections, collected and due this month, open complaints per area.

### The assistant
It has three sources and is honest about each:

| Source | Used for | Example |
|---|---|---|
| Live database (tools) | Account facts | "You have 2 unpaid months, ৳1,600 total." |
| Operator's documents (RAG) | How-to and policy | "A red LOS light means the fibre signal is lost. Check that the yellow cable is not bent..." |
| Neither | Says it does not know | "Our documents don't cover that. Please call the office." |

It never guesses a bill amount, never reveals another customer's data, and stays on the operator's business.

---

## 5. Example conversations

**Bill question (tool)**
> **Customer:** amar bill koto baki?
> **NetDesk:** Apnar 2 masher bill baki ache: September ar October, mot ৳1,600. bKash e pay korte chaile ami step gulo bole dite pari.

**Outage (tool + notice)**
> **Customer:** Net not working since morning.
> **NetDesk:** There is a known fault in Mirpur 10 right now. 14 customers have reported it and the team expects to fix it by 6pm. You don't need to file a complaint; I'll note your connection as affected.

**Troubleshooting (documents)**
> **Customer:** Router e lal batti jolche.
> **NetDesk:** Lal LOS batti mane fibre signal asche na. Prothome dekhun holud cable ta baka ba khola ache kina... *(Source: troubleshooting guide)*

**Nothing found**
> **Customer:** Do you sell Starlink?
> **NetDesk:** I couldn't find anything about that in our documents. I can help with your connection, bills, complaints and our packages.

**Multi-turn**
> **Customer:** How do I pay?
> **NetDesk:** *(explains bKash steps from the payment guide)*
> **Customer:** And if I pay late?
> **NetDesk:** *(answers the late-payment rule, understanding "late" refers to the bill)*

---

## 6. Roles and permissions

| Action | Customer | Technician | Admin |
|---|---|---|---|
| See own connection, bills, complaints | yes | | yes |
| File a complaint | own connection | | yes |
| See all complaints, filter by area | | yes | yes |
| Update complaint status | | yes | yes |
| Create, edit, delete connections and packages | | | yes |
| Create bills, mark paid | | | yes |
| Post outage notice | | | yes |
| Ask assistant about any customer | | by customer code | by customer code |

---

## 7. Why someone would pay

| Today | With NetDesk |
|---|---|
| Phone busy, customers angry | Assistant answers instantly, day and night |
| Fifty calls for one fibre cut | One notice, the assistant tells everyone |
| Paper register, missed bills | Unpaid list in one click |
| Complaints lost in Messenger | A tracked list per area with times |
| Owner guesses monthly collection | Collected and due shown live |

Existing ISP billing software mainly handles billing and line control. NetDesk's difference is the support assistant that reads the operator's own data and documents. Check what local operators use now and adjust this claim after your interview.

---

## 8. Business model

| Item | Price *(assumption)* |
|---|---|
| Monthly fee | ৳3–5 per active connection per month |
| One-time setup | ৳5,000–10,000 for data entry from the operator's register and writing their documents |
| Free trial | First month free |

A 500-connection operator would pay about ৳1,500–2,500 a month *(assumption)*, less than a part-time phone attendant.

**Later income:** SMS reminders charged per message, a white-label customer app, extra branches.

**First customers:** your own ISP, then operators in neighbouring areas through their association or word of mouth.

---

## 9. Scope

**Must have (the graded project)**
- Login with three roles
- Packages, connections, bills, complaints
- Assistant with bill tool, area-complaints tool and document answers
- MCP server for staff tools
- Seed data, documents, Docker, live deployment, frontend

**Should have (makes it feel real)**
- Monthly bill generation
- Payment transaction ID and receiver
- Suspend after unpaid months, reactivate on payment
- Area outage notice
- Owner summary numbers
- Pagination on lists

**Later (say it in the video as the roadmap, do not build)**
- Real bKash payment link
- SMS reminders
- Router status check from the operator's network equipment
- Technician mobile app with map

---

## 10. Documents the operator provides

Short files, in Bangla and English, written from a real operator's answers:

1. Troubleshooting guide: red light, slow speed, wifi connected but no internet, router reset
2. Packages and prices
3. Payment guide: bKash and Nagad steps, due date, late rule
4. Policies: house shift, reconnect fee, holiday support hours, package change
5. FAQ

---

## 11. Questions to ask a real operator

Take 30 minutes at your own ISP's office.

1. How many connections and how many areas?
2. How do you record bills now? When in the month are they due?
3. After how many unpaid months do you cut a line? Is there a reconnect fee?
4. Which payment methods do customers use?
5. What are the three most common calls?
6. What do you tell a customer when the router shows a red light?
7. How do technicians get their jobs today?
8. What happens during a fibre cut?
9. Do you use any software now? What do you dislike about it?
10. Would you pay a small monthly fee per connection for this?

Their answers become your fields, your documents, your seed data and your video story.

---

## 12. Risks and answers

| Risk | Answer |
|---|---|
| Assistant gives a wrong bill amount | Amounts only ever come from the database tool, never from the model's memory |
| A customer sees another's data | The tool reads the user from the login token, not from the chat |
| Assistant invents a policy | It answers only from retrieved documents and says so when nothing matches |
| Weak Bangla answers | Documents in both languages; test Bangla questions early |
| Operators already have billing software | Position NetDesk as the support layer; billing here is simple on purpose |
| Marker sees it as a "shopping/FAQ chatbot" | Lead the video with the outage and bill flows, which need real data |

---

## 13. Demo story for the video

1. **Rahim, a customer in Mirpur 10**, logs in. His net is down. He asks the assistant; it reports the area fault from live complaints.
2. He asks what he owes; the assistant reads his two unpaid bills.
3. He asks how to pay by bKash; the answer comes from the payment guide, with the source shown.
4. He asks something off-topic; the assistant says it found nothing.
5. **The technician** opens the Mirpur 10 complaints list and resolves one.
6. **The owner** marks Rahim's bill paid with a transaction ID, then looks at the month's totals.
7. **MCP:** from a desktop client, the owner asks for a due-bill reminder message for a customer code.

---

## 14. Text for the README

> **NetDesk** is an AI support and billing desk for neighbourhood broadband operators in Bangladesh. Customers ask about outages, bills and router problems in Bangla or English and get answers from the operator's live data and its own guides. Owners and technicians manage connections, bills and complaints from one dashboard.
>
> **Built for:** area broadband operators with 200–2,000 connections.
> **Replaces:** phone calls, paper registers, Excel and Messenger.
> **Pricing:** a small monthly fee per active connection, plus one-time setup.
