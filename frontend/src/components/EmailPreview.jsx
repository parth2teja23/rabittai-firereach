/**
 * EmailPreview.jsx
 * ─────────────────
 * Shows the generated outreach email with subject, body, and send status.
 * Includes a copy-to-clipboard button for the email body.
 */

import { useState } from 'react'
import { Mail, Copy, CheckCheck, Send, AlertTriangle } from 'lucide-react'
import styles from './EmailPreview.module.css'

export default function EmailPreview({ email }) {
  const [copied, setCopied] = useState(false)

  if (!email) return null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`Subject: ${email.subject}\n\n${email.body}`)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard not available */
    }
  }

  return (
    <section className={styles.panel} aria-label="Generated outreach email">
      <div className={styles.panelHeader}>
        <h2 className={styles.title}>
          <Mail size={15} />
          Generated Outreach Email
        </h2>
        <div className={styles.statusChip}>
          {email.sent ? (
            <span className={styles.sent}><Send size={12} /> Sent ✅</span>
          ) : (
            <span className={styles.drafted}>
              <AlertTriangle size={12} />
              {email.error ? 'Send failed' : 'Drafted (SMTP not configured)'}
            </span>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div className={styles.meta}>
        <div className={styles.metaRow}>
          <span className={styles.metaKey}>To</span>
          <span className={styles.metaVal}>{email.to_email}</span>
        </div>
        <div className={styles.metaRow}>
          <span className={styles.metaKey}>Subject</span>
          <span className={styles.metaVal}>{email.subject}</span>
        </div>
        {email.message_id && (
          <div className={styles.metaRow}>
            <span className={styles.metaKey}>Message-ID</span>
            <code className={styles.metaVal} style={{ fontSize: '12px' }}>{email.message_id}</code>
          </div>
        )}
        {email.error && (
          <div className={styles.metaRow}>
            <span className={styles.metaKey} style={{ color: 'var(--red)' }}>Error</span>
            <span className={styles.metaVal} style={{ color: 'var(--red)' }}>{email.error}</span>
          </div>
        )}
      </div>

      {/* Body */}
      <div className={styles.bodyWrapper}>
        <button className={styles.copyBtn} onClick={handleCopy} aria-label="Copy email">
          {copied ? <CheckCheck size={13} /> : <Copy size={13} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
        <pre className={styles.body}>{email.body}</pre>
      </div>
    </section>
  )
}
