# FireReach — Agent Documentation (DOCS.md)

> **Required submission artefact** as per the Rabbitt Agentic AI Developer challenge.

---

## 1. System Prompt (Persona + Constraints)

```
You are FireReach, an elite autonomous GTM (Go-To-Market) intelligence agent.
Your mission: research target companies using live signals and automatically
send hyper-personalised outreach emails on behalf of the seller.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You think like a seasoned enterprise Account Executive combined with a
data journalist. You are methodical, insight-driven, and allergic to generic
sales language.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT CONSTRAINTS (NEVER VIOLATE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. TOOL ORDER IS MANDATORY — always call tools in this exact sequence:
   STEP 1 → tool_signal_harvester
   STEP 2 → tool_research_analyst
   STEP 3 → tool_outreach_automated_sender

2. ZERO-TEMPLATE POLICY — Every email must reference SPECIFIC signals from
   Step 1. Generic phrases like "I hope this finds you well" are forbidden.

3. DO NOT skip any tool. Do not combine steps. Run them in order.

4. After Step 3 completes, summarise what you did in a single concise paragraph.

5. If a tool fails, report the error clearly and stop.
```

---

## 2. Logic Flow

```
User Input (ICP + Target Company + Email)
           │
           ▼
┌──────────────────────────────────┐
│  tool_signal_harvester           │  ← STEP 1: DETERMINISTIC
│  • 6 targeted Tavily queries     │
│  • Funding, hiring, leadership,  │
│    tech changes, growth, security │
│  • Returns: {signals[], summary} │
└──────────────┬───────────────────┘
               │ signals_json
               ▼
┌──────────────────────────────────┐
│  tool_research_analyst           │  ← STEP 2: LLM-POWERED
│  • Input: signals + ICP          │
│  • Output: 2-paragraph brief     │
│    - Pain Points (signal-based)  │
│    - Strategic Alignment (ICP)   │
└──────────────┬───────────────────┘
               │ brief_json
               ▼
┌──────────────────────────────────┐
│  tool_outreach_automated_sender  │  ← STEP 3: LLM + SMTP
│  • Write email (signal-grounded) │
│  • Subject references a signal   │
│  • Body < 180 words              │
│  • Dispatch via aiosmtplib       │
└──────────────────────────────────┘
               │
               ▼
       OutreachResponse
  (steps[], signals, brief, email)
```

### Zero-Template Guarantee

The system prompt instructs the LLM that:
- The **first sentence** must reference a specific live signal  
- Phrases like *"I hope this finds you well"* are explicitly forbidden  
- The email subject line must contain a signal reference (e.g., *"Re: your Series B"*)

---

## 3. Tool Schemas (JSON Schema / OpenAPI style)

### 3.1 `tool_signal_harvester`

**Category:** Deterministic (API-based, no LLM guessing)  
**Data source:** Tavily Search API (real-time web)

```json
{
  "name": "tool_signal_harvester",
  "description": "Fetches live buyer signals for a target company using Tavily web search. Covers funding, leadership changes, hiring trends, tech stack changes, growth signals, and security signals.",
  "parameters": {
    "type": "object",
    "properties": {
      "company": {
        "type": "string",
        "description": "The company name to research, e.g. 'Stripe'"
      }
    },
    "required": ["company"]
  },
  "returns": {
    "type": "string",
    "description": "JSON string with shape: { company: string, signals: [{type, summary, source_url}], raw_summary: string }"
  }
}
```

**Signal types collected:**

| Type | Query pattern |
|------|--------------|
| Funding | `{company} funding round 2024 2025` |
| Leadership Change | `{company} new CTO CFO CEO hire leadership` |
| Hiring Trend | `{company} hiring engineers security roles jobs 2025` |
| Tech Stack Change | `{company} new technology stack tool adoption` |
| Growth Signal | `{company} series A B C investment growth expansion` |
| Security Signal | `{company} cybersecurity breach incident data security 2025` |

---

### 3.2 `tool_research_analyst`

**Category:** LLM-powered (Gemini / Groq)  
**Input grounding:** Always based on signals from Step 1 — never fabricated

```json
{
  "name": "tool_research_analyst",
  "description": "Generates a structured 2-paragraph Account Brief from harvested signals and the seller's ICP. Paragraph 1 = pain points from signals. Paragraph 2 = strategic alignment with the ICP.",
  "parameters": {
    "type": "object",
    "properties": {
      "icp": {
        "type": "string",
        "description": "The seller's Ideal Customer Profile description"
      },
      "signals_json": {
        "type": "string",
        "description": "JSON string returned by tool_signal_harvester"
      },
      "company": {
        "type": "string",
        "description": "Target company name"
      }
    },
    "required": ["icp", "signals_json", "company"]
  },
  "returns": {
    "type": "string",
    "description": "JSON string: { pain_points: string, strategic_alignment: string, full_brief: string }"
  }
}
```

---

### 3.3 `tool_outreach_automated_sender`

**Category:** LLM (email authoring) + SMTP (delivery via aiosmtplib)  
**Zero-Template Policy enforced in prompt**

```json
{
  "name": "tool_outreach_automated_sender",
  "description": "Writes a hyper-personalised outreach email grounded in live signals and account brief, then dispatches it via SMTP automatically.",
  "parameters": {
    "type": "object",
    "properties": {
      "icp":          { "type": "string", "description": "Seller's ICP" },
      "company":      { "type": "string", "description": "Target company name" },
      "signals_json": { "type": "string", "description": "Output from tool_signal_harvester" },
      "brief_json":   { "type": "string", "description": "Output from tool_research_analyst" },
      "to_email":     { "type": "string", "description": "Recipient email address" },
      "sender_name":  { "type": "string", "description": "Sender's name for email sign-off" }
    },
    "required": ["icp", "company", "signals_json", "brief_json", "to_email", "sender_name"]
  },
  "returns": {
    "type": "string",
    "description": "JSON string: { subject, body, to_email, sent: bool, message_id, error }"
  }
}
```

**Email constraints enforced by LLM prompt:**
- First sentence = specific signal reference
- ≤ 180 words body
- Subject contains a signal keyword
- One CTA: 15-minute call with `[CALENDLY_LINK]` placeholder
- No generic openers

---

## 4. Technical Stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini 1.5 Flash (or Groq Llama 3 70B) |
| Agent Framework | LangChain `create_tool_calling_agent` + `AgentExecutor` |
| Signal Harvesting | Tavily Search API (deterministic, real-time) |
| Backend | FastAPI + uvicorn (async) |
| Email Delivery | `aiosmtplib` over SMTP (Gmail-compatible) |
| Frontend | React 18 + Vite + CSS Modules |
| Package Manager | `uv` (backend), npm (frontend) |

---

## 5. Rabbitt Challenge Prompt

**ICP:** *"We sell high-end cybersecurity training to Series B startups."*

**Task:** *"Find companies with recent growth signals and send a personalised outreach email to [candidate-email-here] that connects their expansion to our security training."*

### How FireReach handles this:

1. **tool_signal_harvester** searches for the target company's Series B funding news, rapid hiring (especially engineering), tech stack adoptions, and any security-related mentions — all via live Tavily queries.

2. **tool_research_analyst** interprets those signals through the cybersecurity training ICP lens:  
   - Pain: *"Rapid headcount growth without proportional security training = elevated insider threat and compliance exposure"*  
   - Alignment: *"Our training scales with your engineering team — from SOC basics to advanced red-team simulations"*

3. **tool_outreach_automated_sender** generates an email that opens with the exact signal (e.g., *"I saw you closed your $40M Series B last month and have 15 open engineering roles..."*) and delivers it to the candidate email automatically.

---

## 6. Running Locally

See `README.md` for full setup instructions.
