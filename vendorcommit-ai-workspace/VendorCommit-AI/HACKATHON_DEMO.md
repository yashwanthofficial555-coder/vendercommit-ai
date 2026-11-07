# VendorCommit AI — Hackathon Demo Guide

## One-line pitch

**VendorCommit AI turns scattered supplier conversations into verifiable commitments and uses Hindsight memory to make every negotiation and delivery decision smarter than the last.**

## The problem

Procurement teams repeatedly renegotiate without the full history: prior concessions live in inboxes, supplier preferences live in people’s heads, and delivery warning signs appear only after a breach. A conventional chatbot can summarize a conversation, but it does not create an operational system of accountable promises or show how history changed a decision.

## The innovation

VendorCommit combines an operational commitment ledger with supplier-specific memory and an inspectable before/after decision comparison. It is not a chatbot layered on documents. It connects interactions, commitments, verification, memory, and rule-based intelligence in one workflow. Every memory-assisted recommendation exposes its evidence and provenance.

## Four-minute winning demo

### 1. Start with the operational problem — 35 seconds

Open **Dashboard**. Explain that suppliers, commitments, deadlines, risks, and savings are calculated from database records. Point out that this is a working system of record, not a collection of static analytics cards.

### 2. Show the before/after — 90 seconds

Open **Memory Lab**. Northstar Industrial is selected automatically.

- The **Without memory** card can only recommend a generic supplier review.
- The **With Hindsight memory** card recalls the September volume-discount precedent, the supplier’s rate-hold preference, and the latest negotiated price.
- Click an evidence card to open its provenance, source interaction ID, timestamp, and sync state.

**Narration:** “The system does not merely remember that Northstar is a supplier. It remembers what Northstar conceded, under what conditions, and which interaction proves it.”

### 3. Show learning over time — 60 seconds

In **Teach the agent a new fact**, enter:

> Northstar accepted an additional 2% discount when payment terms were reduced from 45 to 30 days.

Click **Retain and refresh decision**. The new fact is persisted and recalled into the price-negotiation recommendation. Refresh the browser to demonstrate persistence.

For an end-to-end operational learning loop, open **Interactions**, add a negotiation containing a new discount precedent, and return to Memory Lab. New interactions automatically retain their original text with source-interaction provenance; no AI extraction is claimed.

**Narration:** “The next decision improves immediately because a new source fact has joined this supplier’s isolated memory—not because a global prompt was edited.”

### 4. Prove the second use case — 45 seconds

Select **Vertex Components**, then **Delivery planning**. The comparison recalls repeated semiconductor constraints and the requested two-week buffer. This demonstrates that the same memory layer supports risk prevention, not only pricing.

### 5. Close with trust and adoption — 30 seconds

Open **Commitments** and **Interactions**. Explain independent verification, audit tracking, status transitions, and supplier-specific memory isolation. Close on the Memory Lab provenance view.

**Narration:** “VendorCommit is designed for a workflow companies already budget for: procurement operations. The adoption path is email and meeting ingestion first, then ERP integration, while verification provenance keeps a human in control.”

## Judging-criteria alignment

- **Innovation:** A memory-grounded supplier decision system with operational commitments and a visible memory advantage, rather than another chat interface.
- **Use of Hindsight Memory:** Supplier-isolated retention/recall, evidence provenance, persistent learning, two decision scenarios, and an interactive add-fact demonstration. Memory directly changes decision support.
- **Technical Implementation:** FastAPI, SQLAlchemy, Alembic, Pydantic v2, React, repository/service separation, relational constraints, deterministic calculations, and automated tests.
- **User Experience:** A guided operational story from interaction to memory to action, responsive enterprise UI, and inspectable evidence instead of unexplained recommendations.
- **Real-world Impact:** Targets repeatable negotiation preparation, supplier-risk planning, and commitment accountability. The adoption path is procurement teams with fragmented email/meeting histories and existing ERP systems.

## Honesty and demo data

The Northstar, Vertex, and Meridian records are explicitly fictional demo fixtures. All displayed metrics are calculated from those persisted records. `LOCAL_MOCK` performs deterministic local retrieval and never labels its output as AI-generated or cloud-retrieved. The recommendation comparison is rule-based and exposes the exact records it uses. The integrated demo runs a self-hosted Hindsight 1.2.0 server with PostgreSQL persistence, Gemini fact extraction, and Gemini embeddings. VendorCommit connects through the official Hindsight client with isolated supplier banks. All five seeded source records are synchronized and Memory Lab displays Hindsight recall. Local mock remains available as an explicitly labelled fallback.
