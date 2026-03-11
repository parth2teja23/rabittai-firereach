"""
FireReach Agent Tools
=====================
Implements the three required function-calling tools:

1. tool_signal_harvester   – Deterministic, API-based live signal collection (Tavily)
2. tool_research_analyst   – LLM-powered account brief generation
3. tool_outreach_automated_sender – LLM email authoring + SMTP dispatch

Each tool is a plain async Python function decorated with @tool (LangChain).
The agent imports these and registers them in its tool belt.
"""

from __future__ import annotations

import asyncio
import json
import logging
import textwrap
from typing import Annotated

from langchain_core.tools import tool
from tavily import TavilyClient

from config import get_settings
from email_service import send_email

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: build the LLM once (shared across analyst + sender tools)
# ---------------------------------------------------------------------------

def _build_llm():
    """Construct the configured chat model (Gemini or Groq)."""
    cfg = get_settings()
    if cfg.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=cfg.gemini_model,
            google_api_key=cfg.gemini_api_key,
            temperature=0.4,
        )
    else:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=cfg.groq_model,
            groq_api_key=cfg.groq_api_key,
            temperature=0.4,
        )


# ---------------------------------------------------------------------------
# Tool 1 – Signal Harvester (DETERMINISTIC)
# ---------------------------------------------------------------------------

@tool
def tool_signal_harvester(
    company: Annotated[str, "The company name to research, e.g. 'Stripe'"],
) -> str:
    """
    **tool_signal_harvester** — Live Buyer Signal Collection.

    Performs multiple targeted Tavily web searches to discover real, up-to-date
    growth and intent signals for the specified company.

    Signal categories searched:
      • Funding rounds / investment announcements
      • Leadership changes (new C-suite hires)
      • Hiring trends (open engineering / security roles)
      • Technology stack changes / new tool adoptions
      • Competitive signals (switching from incumbent tools)
      • Social mentions & PR activity

    This tool is DETERMINISTIC: it queries real web sources and does NOT
    hallucinate or infer signals. All signals include a source URL.

    Returns a JSON string with:
      - company   : str
      - signals   : list[{type, summary, source_url}]
      - raw_summary : str  (human-readable paragraph)
    """
    cfg = get_settings()
    client = TavilyClient(api_key=cfg.tavily_api_key)

    # Each query targets a specific signal type
    queries = [
        (f"{company} funding round 2024 2025", "Funding"),
        (f"{company} new CTO CFO CEO hire leadership 2024 2025", "Leadership Change"),
        (f"{company} hiring engineers security roles jobs 2025", "Hiring Trend"),
        (f"{company} new technology stack tool adoption announcement", "Tech Stack Change"),
        (f"{company} series A B C investment growth expansion", "Growth Signal"),
        (f"{company} cybersecurity breach incident data security 2025", "Security Signal"),
    ]

    signals: list[dict] = []
    seen_urls: set[str] = set()

    for query, signal_type in queries:
        try:
            results = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_answer=True,
            )
            for r in results.get("results", []):
                url = r.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                snippet = r.get("content", "")[:300].strip()
                if snippet:
                    signals.append({
                        "type": signal_type,
                        "summary": snippet,
                        "source_url": url,
                    })
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tavily query failed for '%s': %s", query, exc)

    if not signals:
        raw_summary = f"No live signals found for {company} at this time."
    else:
        # Build a concise prose summary from the top signals
        lines = [f"- [{s['type']}] {s['summary']} (source: {s['source_url']})" for s in signals[:6]]
        raw_summary = (
            f"Live signals discovered for {company}:\n" + "\n".join(lines)
        )

    result = {
        "company": company,
        "signals": signals[:10],  # cap at 10 signals
        "raw_summary": raw_summary,
    }
    logger.info("signal_harvester found %d signals for %s", len(signals), company)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tool 2 – Research Analyst (LLM)
# ---------------------------------------------------------------------------

@tool
def tool_research_analyst(
    icp: Annotated[str, "The seller's Ideal Customer Profile description"],
    signals_json: Annotated[str, "JSON string returned by tool_signal_harvester"],
    company: Annotated[str, "Target company name"],
) -> str:
    """
    **tool_research_analyst** — Account Brief Generator.

    Takes the live signals harvested by tool_signal_harvester and the seller's
    Ideal Customer Profile (ICP) and produces a structured 2-paragraph
    "Account Brief":

      Paragraph 1 – Pain Points: Specific challenges the company faces based
                    on the detected signals (funding pressure, rapid growth,
                    security exposure, etc.).
      Paragraph 2 – Strategic Alignment: How the ICP offering directly solves
                    those pain points.

    This brief is passed verbatim to tool_outreach_automated_sender so that
    every email is grounded in real, research-backed insights — not guesswork.

    Returns a JSON string with:
      - pain_points          : str
      - strategic_alignment  : str
      - full_brief           : str
    """
    llm = _build_llm()

    try:
        signals_data = json.loads(signals_json)
        raw_summary = signals_data.get("raw_summary", signals_json)
    except json.JSONDecodeError:
        raw_summary = signals_json

    prompt = textwrap.dedent(f"""
        You are a world-class B2B sales research analyst.

        TARGET COMPANY : {company}
        SELLER ICP     : {icp}

        LIVE SIGNALS (from real web search):
        {raw_summary}

        YOUR TASK:
        Write a concise, insight-rich "Account Brief" in EXACTLY two paragraphs.

        PARAGRAPH 1 — Pain Points (3-5 sentences):
        Based ONLY on the live signals above, identify the specific operational,
        technical, or strategic pain points the target company is likely experiencing.
        Be specific; reference the signals (hiring surge, funding round, etc.).

        PARAGRAPH 2 — Strategic Alignment (3-5 sentences):
        Explain precisely how the seller's ICP offering addresses those pain points.
        Connect each pain point to a concrete benefit the seller provides.
        Sound like an insider, not a brochure.

        FORMAT: Return ONLY raw JSON (no markdown fences) in this exact shape:
        {{
          "pain_points": "<paragraph 1 text>",
          "strategic_alignment": "<paragraph 2 text>"
        }}
    """).strip()

    response = llm.invoke(prompt)
    raw_content = response.content
    if isinstance(raw_content, list):
        # Gemini/multi-modal: content is a list of blocks, extract text
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw_content
        ).strip()
    else:
        content = raw_content.strip()

    # Strip potential markdown fences
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    try:
        parsed = json.loads(content)
        pain_points = parsed.get("pain_points", "")
        strategic_alignment = parsed.get("strategic_alignment", "")
    except json.JSONDecodeError:
        # Fallback: treat entire response as the brief
        pain_points = content
        strategic_alignment = ""

    full_brief = f"{pain_points}\n\n{strategic_alignment}".strip()

    result = {
        "pain_points": pain_points,
        "strategic_alignment": strategic_alignment,
        "full_brief": full_brief,
    }
    logger.info("research_analyst produced brief for %s", company)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tool 3 – Outreach Sender (LLM + SMTP)
# ---------------------------------------------------------------------------

@tool
def tool_outreach_automated_sender(
    icp: Annotated[str, "Seller's Ideal Customer Profile"],
    company: Annotated[str, "Target company name"],
    signals_json: Annotated[str, "JSON string from tool_signal_harvester"],
    brief_json: Annotated[str, "JSON string from tool_research_analyst"],
    to_email: Annotated[str, "Recipient email address"],
    sender_name: Annotated[str, "Sender's name for the sign-off"],
) -> str:
    """
    **tool_outreach_automated_sender** — Email Author & Dispatcher.

    This is the execution step of the agentic loop.

    Step A — WRITE: Uses the LLM to craft a hyper-personalised cold outreach email
    that:
      • Opens with a specific signal reference (never generic, never templated)
      • Connects the signal to a pain point identified in the Account Brief
      • Pivots to the seller's solution (ICP) with a concrete value proposition
      • Ends with a single, low-friction CTA (15-min call)
      • Is under 200 words (respects busy executives)
      • Has a compelling, signal-anchored subject line

    Step B — SEND: Dispatches the email automatically via SMTP using the
    configured credentials. No human copy-paste required.

    Returns a JSON string with:
      - subject    : str
      - body       : str
      - to_email   : str
      - sent       : bool
      - message_id : str | null
      - error      : str | null
    """
    cfg = get_settings()
    llm = _build_llm()

    # --- Parse context ---
    try:
        signals_data = json.loads(signals_json)
        raw_summary = signals_data.get("raw_summary", "")
        top_signal = signals_data.get("signals", [{}])[0].get("summary", "") if signals_data.get("signals") else ""
    except Exception:  # noqa: BLE001
        raw_summary = signals_json
        top_signal = ""

    try:
        brief_data = json.loads(brief_json)
        full_brief = brief_data.get("full_brief", brief_json)
    except Exception:  # noqa: BLE001
        full_brief = brief_json

    # --- Step A: Draft email ---
    prompt = textwrap.dedent(f"""
        You are an elite B2B SDR (Sales Development Representative) writing a
        cold outreach email. Your emails are known for feeling hand-crafted,
        never templated.

        SELLER ICP     : {icp}
        SENDER NAME    : {sender_name}
        TARGET COMPANY : {company}
        RECIPIENT      : {to_email}

        ACCOUNT BRIEF (research context):
        {full_brief}

        TOP LIVE SIGNAL:
        {top_signal or raw_summary}

        CONSTRAINTS (STRICT – must follow all):
        1. The FIRST sentence must reference a SPECIFIC live signal about the company
           (funding, hiring, new leadership, tech change). No generic opener.
        2. Under 180 words total in the body.
        3. Zero-Template Policy: do NOT use phrases like "I came across your company"
           or "I hope this email finds you well."
        4. ONE clear CTA: a 15-minute call. Include a Calendly placeholder: [CALENDLY_LINK].
        5. Sign off as {sender_name}.
        6. Subject line must include a signal reference (e.g., "Re: your Series B").

        FORMAT: Return ONLY raw JSON (no markdown, no fences):
        {{
          "subject": "<email subject line>",
          "body": "<full email body, newlines as \\n>"
        }}
    """).strip()

    response = llm.invoke(prompt)
    raw_content = response.content
    if isinstance(raw_content, list):
        # Gemini/multi-modal: content is a list of blocks, extract text
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw_content
        ).strip()
    else:
        content = raw_content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    try:
        email_draft = json.loads(content)
        subject = email_draft.get("subject", f"Quick thought on {company}'s growth")
        body = email_draft.get("body", content)
    except json.JSONDecodeError:
        subject = f"Quick thought on {company}'s growth"
        body = content

    # Normalise newlines
    body = body.replace("\\n", "\n")

    # --- Step B: Send via SMTP ---
    sent, message_id, error = asyncio.run(
        send_email(to=to_email, subject=subject, body=body, cfg=cfg)
    )

    result = {
        "subject": subject,
        "body": body,
        "to_email": to_email,
        "sent": sent,
        "message_id": message_id,
        "error": error,
    }
    logger.info(
        "outreach_sender: sent=%s to=%s subject='%s'",
        sent, to_email, subject,
    )
    return json.dumps(result)


# Public tool registry (imported by agent.py)
ALL_TOOLS = [
    tool_signal_harvester,
    tool_research_analyst,
    tool_outreach_automated_sender,
]
