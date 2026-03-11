/**
 * SignalsPanel.jsx
 * ─────────────────
 * Displays the structured buyer signals discovered by tool_signal_harvester.
 * Each signal is rendered as a card with its type badge, summary, and source link.
 */

import { ExternalLink, Radio } from 'lucide-react'
import styles from './SignalsPanel.module.css'

const TYPE_COLORS = {
  'Funding':          '#f59e0b',
  'Leadership Change':'#8b5cf6',
  'Hiring Trend':     '#06b6d4',
  'Tech Stack Change':'#10b981',
  'Growth Signal':    '#f97316',
  'Security Signal':  '#ef4444',
}

function SignalCard({ signal }) {
  const color = TYPE_COLORS[signal.type] || '#6b7280'
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span
          className={styles.typeBadge}
          style={{ background: color + '1a', color, borderColor: color + '44' }}
        >
          {signal.type}
        </span>
        {signal.source_url && (
          <a
            href={signal.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.sourceLink}
            title="Open source"
          >
            <ExternalLink size={12} />
            Source
          </a>
        )}
      </div>
      <p className={styles.summary}>{signal.summary}</p>
    </div>
  )
}

export default function SignalsPanel({ signals }) {
  if (!signals) return null

  return (
    <section className={styles.panel} aria-label="Harvested buyer signals">
      <h2 className={styles.title}>
        <Radio size={15} />
        Live Signals — {signals.company}
        <span className={styles.count}>{signals.signals.length} found</span>
      </h2>

      <p className={styles.summary}>{signals.raw_summary}</p>

      {signals.signals.length > 0 && (
        <div className={styles.grid}>
          {signals.signals.map((s, i) => (
            <SignalCard key={i} signal={s} />
          ))}
        </div>
      )}
    </section>
  )
}
