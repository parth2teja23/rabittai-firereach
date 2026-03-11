/**
 * App.jsx – FireReach Dashboard
 * ══════════════════════════════
 * Single-page React application that drives the FireReach autonomous
 * outreach pipeline.
 *
 * Layout:
 *   ┌─────────────────────────────────────────────────────┐
 *   │ Header (logo + tagline)                              │
 *   ├────────────────────┬────────────────────────────────┤
 *   │  LEFT PANEL        │  RIGHT PANEL                   │
 *   │  OutreachForm      │  AgentLog                      │
 *   │                    │  SignalsPanel                  │
 *   │                    │  BriefPanel                    │
 *   │                    │  EmailPreview                  │
 *   └────────────────────┴────────────────────────────────┘
 *
 * Data flow:
 *   1. User fills form → handleSubmit posts to POST /api/outreach
 *   2. Response populates result state
 *   3. Child components render based on result.*
 */

import { useState } from 'react'
import axios from 'axios'
import { Flame, Github, FileText } from 'lucide-react'

import OutreachForm from './components/OutreachForm.jsx'
import AgentLog     from './components/AgentLog.jsx'
import SignalsPanel from './components/SignalsPanel.jsx'
import BriefPanel   from './components/BriefPanel.jsx'
import EmailPreview from './components/EmailPreview.jsx'

import styles from './App.module.css'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function App() {
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState(null)   // OutreachResponse
  const [apiError, setApiError] = useState(null)

  /**
   * Submit the outreach request to the FastAPI backend.
   * The backend runs the full agentic loop synchronously and returns
   * a structured OutreachResponse with all steps + results.
   */
  const handleSubmit = async (formData) => {
    setLoading(true)
    setResult(null)
    setApiError(null)

    try {
      const res = await axios.post(`${API_BASE}/api/outreach`, formData, {
        timeout: 120_000,   // 2-minute timeout for the full agent run
      })
      setResult(res.data)
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.message ||
        'Unknown error'
      setApiError(String(detail))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.app}>
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.logo}>
          <Flame size={22} className={styles.logoIcon} />
          <span className={styles.logoText}>FireReach</span>
          <span className={styles.logoBadge}>beta</span>
        </div>
        <p className={styles.tagline}>
          Autonomous outreach engine: live signals → account research → personalised email
        </p>
        <div className={styles.headerLinks}>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.headerLink}
          >
            <Github size={14} /> GitHub
          </a>
          <a href="/DOCS.md" target="_blank" className={styles.headerLink}>
            <FileText size={14} /> Docs
          </a>
        </div>
      </header>

      {/* ── Main layout ────────────────────────────────────────────── */}
      <main className={styles.main}>
        {/* Left: input panel */}
        <aside className={styles.left}>
          <div className={styles.card}>
            <h1 className={styles.cardTitle}>Configure Outreach</h1>
            <p className={styles.cardSub}>
              The agent will harvest live signals, research the account, and
              send a signal-grounded email — all autonomously.
            </p>
            <OutreachForm onSubmit={handleSubmit} loading={loading} />
          </div>

          {/* Tool reference */}
          <div className={`${styles.card} ${styles.toolCard}`}>
            <h3 className={styles.toolTitle}>Agent Toolbelt</h3>
            <ol className={styles.toolList}>
              <li>
                <code>tool_signal_harvester</code>
                <span>Tavily web search — live signals</span>
              </li>
              <li>
                <code>tool_research_analyst</code>
                <span>LLM account brief from signals + ICP</span>
              </li>
              <li>
                <code>tool_outreach_automated_sender</code>
                <span>LLM email authoring + SMTP dispatch</span>
              </li>
            </ol>
          </div>
        </aside>

        {/* Right: results panel */}
        <section className={styles.right} aria-live="polite">
          {/* Error */}
          {apiError && (
            <div className={styles.errorBox} role="alert">
              <strong>Error:</strong> {apiError}
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className={styles.loadingBox}>
              <div className={styles.loadingSpinner} aria-hidden="true" />
              <div>
                <p className={styles.loadingTitle}>Agent running…</p>
                <p className={styles.loadingDesc}>
                  Harvesting signals → generating brief → composing email
                </p>
              </div>
            </div>
          )}

          {/* Results */}
          {result && !loading && (
            <>
              <AgentLog     steps={result.steps}   />
              <SignalsPanel signals={result.signals} />
              <BriefPanel   brief={result.brief}    />
              <EmailPreview email={result.email}    />
            </>
          )}

          {/* Empty state */}
          {!result && !loading && !apiError && (
            <div className={styles.emptyState}>
              <Flame size={48} className={styles.emptyIcon} />
              <p className={styles.emptyTitle}>Ready to fire</p>
              <p className={styles.emptyDesc}>
                Fill in the form and click <strong>Launch FireReach Agent</strong>.
                The agent will run all three tools and deliver a signal-grounded
                outreach email.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
