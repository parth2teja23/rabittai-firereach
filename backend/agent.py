"""
FireReach Agentic Core
======================
Uses LangGraph's `create_react_agent` (the modern LangChain 1.x API) to
orchestrate the three tools in strict sequential order:

  Signal Capture  →  Contextual Research  →  Automated Email Delivery

Architecture:
  - `create_react_agent` builds a ReAct graph from the LLM + tool definitions.
  - The graph is invoked with a rich system prompt that enforces tool ordering
    and the zero-template policy.
  - Intermediate tool call / result messages are parsed from the returned
    message list to reconstruct per-step results for the frontend.

LangGraph message flow:
  HumanMessage  →  AIMessage (tool_call)  →  ToolMessage (result)
               →  AIMessage (tool_call)  →  ToolMessage (result)
               →  ...
               →  AIMessage (final response)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from config import get_settings
from models import (
    AccountBrief,
    AgentStatus,
    AgentStep,
    EmailResult,
    OutreachRequest,
    OutreachResponse,
    SignalResult,
)
from tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt  (Persona + Constraints)
# ---------------------------------------------------------------------------

FIREREACH_SYSTEM_PROMPT = """\
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
   STEP 1 → tool_signal_harvester   (collect live signals for the company)
   STEP 2 → tool_research_analyst   (generate account brief from signals + ICP)
   STEP 3 → tool_outreach_automated_sender  (write & send the personalised email)

2. ZERO-TEMPLATE POLICY — Every email must reference SPECIFIC signals from
   Step 1. Generic phrases like "I hope this finds you well" are forbidden.

3. DO NOT skip any tool. Do not combine steps. Run them in order.

4. After Step 3 completes, summarise what you did in a single concise paragraph.

5. If a tool fails, report the error clearly and stop.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After all three tools succeed, reply with:
"Outreach complete. Signal-grounded email sent to [email]. Summary: ..."
"""


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def _build_llm():
    """Construct the configured chat model (Gemini or Groq)."""
    cfg = get_settings()
    if cfg.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=cfg.gemini_model,
            google_api_key=cfg.gemini_api_key,
            temperature=0,
        )
    else:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=cfg.groq_model,
            groq_api_key=cfg.groq_api_key,
            temperature=0,
        )


# ---------------------------------------------------------------------------
# Public run function
# ---------------------------------------------------------------------------

def run_outreach_agent(request: OutreachRequest) -> OutreachResponse:
    """
    Execute the full FireReach agentic loop for the given outreach request.

    Uses LangGraph's `create_react_agent` — the recommended agent pattern in
    LangChain / LangGraph 1.x. The agent receives the system prompt, the three
    tools, and a structured human task, then autonomously calls each tool
    in the specified order.

    Intermediate tool results are extracted from the returned message list so
    the frontend can render a detailed per-step reasoning log.

    Args:
        request: Validated OutreachRequest from the FastAPI layer.

    Returns:
        OutreachResponse with signals, brief, email, and all reasoning steps.
    """
    steps: list[AgentStep] = []

    steps.append(AgentStep(
        status=AgentStatus.STARTED,
        message=f"FireReach agent started for target: {request.company}",
    ))

    llm = _build_llm()

    # Build the LangGraph ReAct agent — system prompt injected here
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=FIREREACH_SYSTEM_PROMPT,
    )

    # Human-readable task that gives the agent all context it needs
    task = (
        f"ICP: \"{request.icp}\"\n\n"
        f"Task: Find companies with recent growth signals and send a personalised "
        f"outreach email to {request.to_email} that connects their expansion to our "
        f"offering.\n\n"
        f"Target company: {request.company}\n"
        f"Sender name: {request.sender_name}\n\n"
        f"Execute all three tools in order:\n"
        f"1. tool_signal_harvester(company=\"{request.company}\")\n"
        f"2. tool_research_analyst(icp=<icp>, signals_json=<step1_output>, company=\"{request.company}\")\n"
        f"3. tool_outreach_automated_sender(icp=<icp>, company=\"{request.company}\", "
        f"signals_json=<step1_output>, brief_json=<step2_output>, "
        f"to_email=\"{request.to_email}\", sender_name=\"{request.sender_name}\")"
    )

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content=task)]},
            config={"recursion_limit": 20},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Agent invocation failed: %s", exc)
        steps.append(AgentStep(
            status=AgentStatus.ERROR,
            message=f"Agent failed: {exc}",
        ))
        return OutreachResponse(success=False, steps=steps, error=str(exc))

    # --- Parse message chain to extract per-tool results ---
    signals_result: SignalResult | None = None
    brief_result: AccountBrief | None = None
    email_result: EmailResult | None = None

    messages = result.get("messages", [])

    # Map tool_call_id → tool_name from all AIMessages that contain tool calls
    tool_call_id_to_name: dict[str, str] = {}
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_call_id_to_name[tc["id"]] = tc["name"]

    # Process ToolMessages (one per tool invocation)
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue

        tool_name = tool_call_id_to_name.get(msg.tool_call_id, "unknown")
        raw_output = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)

        try:
            parsed_output: dict[str, Any] = json.loads(raw_output)
        except (json.JSONDecodeError, TypeError):
            parsed_output = {"raw": raw_output}

        logger.debug("Tool '%s' result (first 300): %s", tool_name, raw_output[:300])

        # ── Signal Harvester ────────────────────────────────────────────────
        if tool_name == "tool_signal_harvester":
            n_signals = len(parsed_output.get("signals", []))
            steps.append(AgentStep(
                status=AgentStatus.HARVESTING,
                tool_name=tool_name,
                message=f"Harvested {n_signals} live signals for {request.company}.",
                data=parsed_output,
            ))
            signals_result = SignalResult(
                company=parsed_output.get("company", request.company),
                signals=parsed_output.get("signals", []),
                raw_summary=parsed_output.get("raw_summary", ""),
            )

        # ── Research Analyst ────────────────────────────────────────────────
        elif tool_name == "tool_research_analyst":
            steps.append(AgentStep(
                status=AgentStatus.RESEARCHING,
                tool_name=tool_name,
                message="Account brief generated.",
                data=parsed_output,
            ))
            brief_result = AccountBrief(
                pain_points=parsed_output.get("pain_points", ""),
                strategic_alignment=parsed_output.get("strategic_alignment", ""),
                full_brief=parsed_output.get("full_brief", ""),
            )

        # ── Outreach Sender ─────────────────────────────────────────────────
        elif tool_name == "tool_outreach_automated_sender":
            sent = parsed_output.get("sent", False)
            steps.append(AgentStep(
                status=AgentStatus.SENDING,
                tool_name=tool_name,
                message=(
                    f"Email {'sent ✅' if sent else 'drafted (SMTP not configured)'} "
                    f"to {request.to_email}."
                ),
                data=parsed_output,
            ))
            email_result = EmailResult(
                subject=parsed_output.get("subject", ""),
                body=parsed_output.get("body", ""),
                to_email=parsed_output.get("to_email", request.to_email),
                sent=sent,
                message_id=parsed_output.get("message_id"),
                error=parsed_output.get("error"),
            )

    # Final textual summary from the last non-empty AIMessage
    final_output = ""
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        c = msg.content
        if isinstance(c, list):
            # Gemini returns content blocks — extract text parts
            c = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in c
            )
        if isinstance(c, str) and c.strip():
            final_output = c.strip()
            break

    steps.append(AgentStep(
        status=AgentStatus.DONE,
        message=final_output or "Agent completed all three tools successfully.",
    ))

    return OutreachResponse(
        success=True,
        steps=steps,
        signals=signals_result,
        brief=brief_result,
        email=email_result,
    )
