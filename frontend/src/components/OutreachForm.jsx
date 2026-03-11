/**
 * OutreachForm.jsx
 * ─────────────────
 * Controlled form that collects the four inputs required to run the
 * FireReach agentic pipeline:
 *   • ICP (Ideal Customer Profile)
 *   • Target company name
 *   • Recipient email address
 *   • Sender name
 *
 * Pre-fills the "Rabbitt Challenge" scenario so testers can click once.
 */

import { useState } from 'react'
import { Zap, Building2, Mail, User, Info } from 'lucide-react'
import styles from './OutreachForm.module.css'

const CHALLENGE_PRESET = {
  icp: 'We sell high-end cybersecurity training to Series B startups.',
  company: 'Stripe',
  to_email: '',           // filled by user
  sender_name: 'Alex Rivera',
}

export default function OutreachForm({ onSubmit, loading }) {
  const [form, setForm] = useState(CHALLENGE_PRESET)

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit(form)
  }

  const handlePreset = () => setForm(CHALLENGE_PRESET)

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-label="Outreach configuration">
      {/* Challenge Preset Banner */}
      <div className={styles.presetBanner}>
        <Info size={15} />
        <span>
          Pre-loaded with the <strong>Rabbitt Challenge</strong> scenario.
          Enter your email &amp; fire away.
        </span>
        <button type="button" className={styles.presetBtn} onClick={handlePreset}>
          Reset to challenge
        </button>
      </div>

      {/* ICP */}
      <label className={styles.field}>
        <span className={styles.label}>
          <Zap size={14} className={styles.icon} />
          Ideal Customer Profile (ICP)
        </span>
        <textarea
          className={styles.textarea}
          rows={3}
          value={form.icp}
          onChange={set('icp')}
          placeholder="We sell … to …"
          required
          minLength={10}
          maxLength={1000}
        />
        <span className={styles.hint}>Describe what you sell and to whom.</span>
      </label>

      {/* Company */}
      <label className={styles.field}>
        <span className={styles.label}>
          <Building2 size={14} className={styles.icon} />
          Target Company
        </span>
        <input
          className={styles.input}
          type="text"
          value={form.company}
          onChange={set('company')}
          placeholder="e.g. Stripe, Notion, Figma"
          required
          minLength={2}
          maxLength={200}
        />
      </label>

      {/* Email */}
      <label className={styles.field}>
        <span className={styles.label}>
          <Mail size={14} className={styles.icon} />
          Recipient Email
        </span>
        <input
          className={styles.input}
          type="email"
          value={form.to_email}
          onChange={set('to_email')}
          placeholder="candidate@example.com"
          required
        />
        <span className={styles.hint}>The outreach email will be sent here.</span>
      </label>

      {/* Sender */}
      <label className={styles.field}>
        <span className={styles.label}>
          <User size={14} className={styles.icon} />
          Sender Name
        </span>
        <input
          className={styles.input}
          type="text"
          value={form.sender_name}
          onChange={set('sender_name')}
          placeholder="Your name"
          maxLength={100}
        />
      </label>

      {/* Submit */}
      <button
        className={styles.submitBtn}
        type="submit"
        disabled={loading}
        aria-busy={loading}
      >
        {loading ? (
          <>
            <span className={styles.spinner} aria-hidden="true" />
            Agent running…
          </>
        ) : (
          <>
            <Zap size={16} />
            Launch FireReach Agent
          </>
        )}
      </button>
    </form>
  )
}
