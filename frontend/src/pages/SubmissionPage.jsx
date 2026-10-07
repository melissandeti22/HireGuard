import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { classifyPosting } from "../api/client";

// Matches the sourced platforms in the data collection pipeline
// (common/config.py: UNIFIED_COLUMNS "source" field).
const SOURCE_OPTIONS = ["BrighterMonday", "Fuzu", "Other"];

// TODO: replace with the authenticated user's id once auth is built.
const PLACEHOLDER_USER_ID = "demo-user";

export default function SubmissionPage() {
  const [text, setText] = useState("");
  const [sourcePlatform, setSourcePlatform] = useState(SOURCE_OPTIONS[0]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

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
      navigate("/results", { state: { result } });
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
      <h1>Submit a Job Posting for Analysis</h1>
      <p className="page-subtitle">
        Paste the full job posting text below, including title, description, and requirements.
      </p>

      <form onSubmit={handleSubmit}>
        <textarea
          className="posting-textarea"
          placeholder="Paste job posting text here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={14}
        />

        <div className="submission-controls">
          <select
            className="source-select"
            value={sourcePlatform}
            onChange={(e) => setSourcePlatform(e.target.value)}
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>Source: {opt}</option>
            ))}
          </select>

          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Analysing..." : "Analyse Posting"}
          </button>
        </div>

        {error && <p className="error-text">{error}</p>}
      </form>

      <p className="footer-note">
        HireGuard uses stylometric analysis and does not store personally identifiable information.
      </p>
    </div>
  );
}
