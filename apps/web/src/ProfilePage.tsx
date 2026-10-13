import { useEffect, useState, type FormEvent } from 'react'
import { fetchProfile, saveProfile, type AthleteProfile } from './api'

const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'

export default function ProfilePage({ token, onTokenChange, onSignIn }: {
  token: string; onTokenChange: (token: string) => void; onSignIn: () => void
}) {
  const [profile, setProfile] = useState<AthleteProfile | null>(null)
  const [name, setName] = useState('')
  const [threshold, setThreshold] = useState('157')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    setLoading(true)
    setError('')
    fetchProfile(apiBase, token).then((data) => {
      if (cancelled) return
      setProfile(data)
      setName(data.name ?? '')
      setThreshold(String(data.threshold_heart_rate_bpm))
    }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not load your profile.')
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, onTokenChange, retry])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      const data = await saveProfile(apiBase, token, { name, threshold_heart_rate_bpm: Number(threshold) })
      setProfile(data)
      setName(data.name ?? '')
      setThreshold(String(data.threshold_heart_rate_bpm))
      setSaved(true)
    } catch (reason) {
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not save your profile. Please try again.')
    } finally { setSaving(false) }
  }

  return <main id="main" className="profile-page">
    <div className="dashboard-heading"><div><span className="eyebrow">YOUR TRAINING SETTINGS</span><h1>Profile</h1><p>Your name and heart-rate threshold for activity TSS estimates.</p></div></div>
    {!token ? <section className="full-detail-section"><h2>Sign in to edit your profile</h2><button className="header-auth" type="button" onClick={onSignIn}>Sign in</button></section>
      : loading ? <p className="dashboard-state" role="status">Loading your profile…</p>
        : !profile ? <section className="full-detail-section"><p role="alert">{error}</p><button className="header-auth" type="button" onClick={() => setRetry((count) => count + 1)}>Try again</button></section>
          : <section className="full-detail-section" aria-labelledby="profile-settings"><h2 id="profile-settings">Personal details</h2>
            <form onSubmit={save} onChange={() => setSaved(false)}>
              <fieldset disabled={saving}>
                <label htmlFor="profile-name">Name</label>
                <input className="text-field" id="profile-name" autoComplete="name" maxLength={100} required value={name} onChange={(event) => setName(event.target.value)} />
                <label className="field-label" htmlFor="profile-threshold">Threshold heart rate (bpm)</label>
                <input className="text-field" id="profile-threshold" type="number" min="30" max="250" step="1" required value={threshold} onChange={(event) => setThreshold(event.target.value)} aria-describedby="profile-threshold-help" />
                <p className="muted" id="profile-threshold-help">Starts at 157 bpm. This is your heart-rate threshold, not your TSS score. Saving a change updates estimates the next time you open an activity.</p>
                <button className="submit" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button>
              </fieldset>
            </form>
            {error && <p className="error-message" role="alert">{error}</p>}
            <p role="status">{saved ? 'Profile saved. Activities will use your saved threshold.' : ''}</p>
            <a className="full-detail-link" href="#activities">Back to activities <span aria-hidden="true">→</span></a>
          </section>}
  </main>
}
