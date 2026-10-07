import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { classifyPosting } from "../api/client";
import { EyeIcon, LockIcon, PenIcon, SparkIcon } from "../components/Icons";

// Matches the sourced platforms in the data collection pipeline
// (common/config.py: UNIFIED_COLUMNS "source" field).
const SOURCE_OPTIONS = ["BrighterMonday", "Fuzu", "Other"];

// TODO: replace with the authenticated user's id once auth is built.
const PLACEHOLDER_USER_ID = "demo-user";

// Fictional postings for quick demos; the first trips the stub heuristic
// (free email + urgency terms), the second does not.
const SAMPLES = [
  {
    label: "Suspicious sample",
    text:
      "URGENT HIRING!!! Data entry clerks needed in Nairobi. Earn KES 80,000 per month " +
      "working from home, no experience needed. Limited slots, act now! Send your CV and a " +
      "registration fee of KES 1,500 via M-Pesa, then email recruit.jobs.ke@gmail.com for your start date.",
  },
  {
    label: "Genuine-looking sample",
    text:
      "Tamarind Freight Ltd is recruiting an Accounts Assistant for our Mombasa office. " +
      "Reporting to the Finance Manager, you will prepare supplier reconciliations, process " +
      "invoices and support month-end close. Requirements: CPA Part II or a degree in Commerce, " +
      "and at least two years of experience with Sage or QuickBooks. Applications close on " +
      "31 October and should be submitted through the careers page on our website.",
  },
];

const FEATURES = [
  {
    icon: PenIcon,
    title: "Writing-style analysis",
    body: "Measures vocabulary, sentence structure, punctuation and readability, the subtle fingerprints scammers leave behind.",
  },
  {
    icon: EyeIcon,
    title: "Explained, not just flagged",
    body: "Every warning comes with the specific signals behind it, so you understand the verdict.",
  },
  {
    icon: LockIcon,
    title: "Privacy first",
    body: "Only the posting text is analysed. No personal data about you is collected.",
  },
];

export default function SubmissionPage() {
  const [text, setText] = useState("");
  const [sourcePlatform, setSourcePlatform] = useState(SOURCE_OPTIONS[0]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim()) {
      setError("Please paste the job posting text before submitting.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await classifyPosting({
        text,
        sourcePlatform,
        userId: PLACEHOLDER_USER_ID,
      });
      navigate("/results", { state: { result, text } });
    } catch (err) {
      setError(
        err.response?.data?.error || "Something went wrong analysing this posting. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page">
      <section className="hero">
        <span className="eyebrow"><SparkIcon size={14} /> Job scam detector for Kenya</span>
        <h1>Is that job offer <span className="hero-accent">too good to be true?</span></h1>
        <p className="hero-sub">
          Paste any job posting and HireGuard will analyse how it's written to spot the
          tell-tale signs of recruitment fraud before you share your details or pay a cent.
        </p>
      </section>

      <form className="card submit-card" onSubmit={handleSubmit}>
        <div className="card-header">
          <label htmlFor="posting-text" className="field-label">Job posting text</label>
          <div className="sample-buttons">
            <span className="muted-small">Try:</span>
            {SAMPLES.map((s) => (
              <button
                key={s.label}
                type="button"
                className="chip"
                onClick={() => { setText(s.text); setError(null); }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        <textarea
          id="posting-text"
          className="posting-textarea"
          placeholder="Paste the full posting here, including the title, description, requirements and how to apply…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={11}
        />
        <div className="textarea-meta">
          <span>{wordCount} {wordCount === 1 ? "word" : "words"}</span>
          {text && (
            <button type="button" className="link-button" onClick={() => setText("")}>Clear</button>
          )}
        </div>

        <div className="submission-controls">
          <div className="segmented" role="radiogroup" aria-label="Where did you find this posting?">
            <span className="segmented-label">Found on</span>
            {SOURCE_OPTIONS.map((opt) => (
              <button
                key={opt}
                type="button"
                role="radio"
                aria-checked={sourcePlatform === opt}
                className={sourcePlatform === opt ? "active" : ""}
                onClick={() => setSourcePlatform(opt)}
              >
                {opt}
              </button>
            ))}
          </div>

          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? (<><span className="spinner" /> Analysing…</>) : "Analyse posting"}
          </button>
        </div>

        {error && <p className="error-text" role="alert">{error}</p>}
      </form>

      <section className="feature-grid">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <div key={title} className="feature-tile">
            <span className="feature-icon"><Icon size={20} /></span>
            <h3>{title}</h3>
            <p>{body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
