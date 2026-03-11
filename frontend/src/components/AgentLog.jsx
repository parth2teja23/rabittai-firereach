/**
 * AgentLog.jsx
 * ─────────────
 * Renders the real-time reasoning log of the FireReach agent.
 * Each AgentStep from the backend is shown as a timeline entry
 * with status badge, tool name, and message.
 *
 * Status colour mapping:
 *   started     → blue
 *   harvesting  → yellow (signal collection in progress)
 *   researching → purple
 *   sending     → orange
 *   done        → green
 *   error       → red
 */

import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import styles from './AgentLog.module.css'

const STATUS_META = {
  started:     { label: 'Started',     color: '#3b82f6' },
  harvesting:  { label: 'Harvesting',  color: '#eab308' },
  researching: { label: 'Researching', color: '#a855f7' },
  sending:     { label: 'Sending',     color: '#f97316' },
  done:        { label: 'Done ✅',     color: '#22c55e' },
  error:       { label: 'Error ❌',    color: '#ef4444' },
}

function StepRow({ step, index }) {
  const [expanded, setExpanded] = useState(false)
  const meta = STATUS_META[step.status] || { label: step.status, color: '#6b7280' }
  const hasData = step.data && Object.keys(step.data).length > 0

  return (
    <div className={styles.step}>
      {/* Timeline connector */}
      <div className={styles.connector}>
        <div className={styles.dot} style={{ background: meta.color }} />
        <div className={styles.line} />
      </div>

      <div className={styles.body}>
        <div className={styles.header}>
          <span className={styles.badge} style={{ background: meta.color + '22', color: meta.color, borderColor: meta.color + '55' }}>
            {meta.label}
          </span>
          {step.tool_name && (
            <code className={styles.toolName}>{step.tool_name}</code>
          )}
          <span className={styles.message}>{step.message}</span>

          {hasData && (
            <button
              className={styles.expandBtn}
              onClick={() => setExpanded((v) => !v)}
              aria-expanded={expanded}
              aria-label="Toggle raw data"
            >
              {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span>{expanded ? 'Hide' : 'Show'} raw data</span>
            </button>
          )}
        </div>

        {expanded && hasData && (
          <pre className={styles.raw}>
            {JSON.stringify(step.data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}

export default function AgentLog({ steps }) {
  if (!steps || steps.length === 0) return null

  return (
    <section className={styles.log} aria-label="Agent reasoning log">
      <h2 className={styles.title}>Agent Reasoning Log</h2>
      <div className={styles.timeline}>
        {steps.map((step, i) => (
          <StepRow key={i} step={step} index={i} />
        ))}
      </div>
    </section>
  )
}
