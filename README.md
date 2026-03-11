# 🔥 FireReach – Autonomous Outreach Engine

> **Rabbitt AI – Agentic AI Developer Challenge submission**

FireReach is a lightweight autonomous GTM agent that:
1. **Harvests live buyer signals** (funding, hiring, leadership changes) via [Tavily](https://tavily.com)
2. **Generates a signal-grounded account brief** using an LLM (Gemini / Groq)
3. **Writes and automatically sends** a hyper-personalised cold email via SMTP

No templates. No manual copy-paste. Full signal → research → send loop.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | **FastAPI** + Python 3.11+ |
| Agent | **LangChain** `create_tool_calling_agent` |
| Signals | **Tavily** Search API |
| LLM | **Google Gemini 1.5 Flash** (or Groq Llama 3) |
| Email | `aiosmtplib` (async SMTP) |
| Frontend | **React 18** + **Vite** |
| Package Mgr | **`uv`** (backend) · npm (frontend) |

---

## Project Structure

```
firereach/
├── backend/
│   ├── pyproject.toml     # uv project manifest
│   ├── .env.example       # environment variable template
│   ├── config.py          # pydantic-settings config
│   ├── models.py          # Pydantic request/response schemas
│   ├── tools.py           # Three LangChain tools
│   ├── agent.py           # AgentExecutor orchestration
│   ├── email_service.py   # aiosmtplib email delivery
│   └── main.py            # FastAPI app
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── App.module.css
│       ├── index.css
│       └── components/
│           ├── OutreachForm.jsx   # ICP + company + email form
│           ├── AgentLog.jsx       # Real-time reasoning steps
│           ├── SignalsPanel.jsx   # Harvested buyer signals
│           ├── BriefPanel.jsx     # Account brief cards
│           └── EmailPreview.jsx   # Generated email + send status
├── DOCS.md   # Agent documentation (required by challenge)
└── README.md
```

---

## Quick Start

### Prerequisites

- [uv](https://github.com/astral-sh/uv) — `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js 18+
- API keys: [Tavily](https://tavily.com), [Gemini](https://aistudio.google.com/app/apikey) (or [Groq](https://console.groq.com))
- Gmail App Password for SMTP (or any SMTP credentials)

---

### 1. Backend Setup

```bash
cd backend

# Install dependencies with uv (scripts-only project, no package to install)
uv sync --no-install-project

# Copy and fill environment variables
cp .env.example .env
# Edit .env with your API keys
```

Start the backend:

```bash
uv run uvicorn main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

### 3. Run the Rabbitt Challenge

In the UI:
- **ICP:** `We sell high-end cybersecurity training to Series B startups.`
- **Target Company:** `Stripe` (or any company with recent news)
- **Recipient Email:** your email address
- Click **Launch FireReach Agent**

The agent will:
1. Run `tool_signal_harvester` → discover live signals
2. Run `tool_research_analyst` → generate account brief
3. Run `tool_outreach_automated_sender` → write + send email

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `gemini` or `groq` |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GEMINI_MODEL` | Default: `gemini-3-flash-preview` |
| `GROQ_API_KEY` | Groq API key |
| `GROQ_MODEL` | Default: `llama3-70b-8192` |
| `TAVILY_API_KEY` | Tavily Search API key |
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | e.g. `587` |
| `SMTP_USER` | Sender email address |
| `SMTP_PASSWORD` | Gmail App Password |
| `SMTP_FROM_NAME` | Display name in From header |
| `CORS_ORIGINS` | JSON array of allowed origins |

---

## API Reference

### `POST /api/outreach`

```json
{
  "icp": "We sell high-end cybersecurity training to Series B startups.",
  "company": "Stripe",
  "to_email": "candidate@example.com",
  "sender_name": "Alex Rivera"
}
```

**Response:** `OutreachResponse` with `steps[]`, `signals`, `brief`, `email`.

Full schema available at `http://localhost:8000/docs`.

---

## Deployment

### Backend (Render)

1. Connect your GitHub repo to [render.com](https://render.com)
2. New → **Web Service**
3. Runtime: **Python 3.11**
4. Build command: `pip install uv && uv sync --no-install-project --no-dev`
5. Start command: `uv run uvicorn main:app --host 0.0.0.0 --port 10000`
6. Add all environment variables in the Render dashboard

### Frontend (Vercel)

1. Import repo on [vercel.com](https://vercel.com)
2. Framework preset: **Vite**
3. Root directory: `frontend`
4. Add env var: `VITE_API_URL=https://your-render-backend.onrender.com`

---

## Documentation

See [DOCS.md](./DOCS.md) for:
- System prompt (persona + constraints)
- Full logic flow diagram
- Tool schemas (JSON Schema)
- Rabbitt Challenge walkthrough

---

## Evaluation Rubric Checklist

| Category | ✅ |
|----------|---|
| Tool Chaining: Signal → Research → Send | ✅ |
| Zero-Template Policy enforced | ✅ |
| Email references live signals | ✅ |
| Automated SMTP dispatch | ✅ |
| React dashboard with agent log | ✅ |
| DOCS.md with schemas + system prompt | ✅ |
# rabittai-firereach
