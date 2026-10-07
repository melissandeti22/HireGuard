import { useLocation, useNavigate } from "react-router-dom";
import { AlertIcon, ArrowLeftIcon, CheckIcon, FlagIcon, InfoIcon } from "../components/Icons";

const FRAUD_TIPS = [
  "Never pay a registration, training or medical fee to get a job.",
  "Don't share your ID, KRA PIN or M-Pesa details until you've verified the employer.",
  "Look up the company independently: an official website, office address and landline.",
  "Be wary of recruiters who only use Gmail, Yahoo or WhatsApp.",
];

const LEGIT_TIPS = [
  "Still confirm the company exists and the role is listed on its official website.",
  "Legitimate employers never ask you to pay to apply or to secure an interview.",
];

function ConfidenceRing({ value, tone }) {
  return (
    <div className={`confidence-ring ring-${tone}`} style={{ "--value": value }}>
      <div className="confidence-ring-inner">
        <strong>{value}%</strong>
        <span>confidence</span>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result;
  const postingText = location.state?.text;

  if (!result) {
    // Direct navigation to /results with no state -- send them back to submit one.
    return (
      <div className="page">
        <div className="card empty-state">
          <span className="empty-icon"><InfoIcon size={26} /></span>
          <h2>No result to show yet</h2>
          <p>Submit a job posting and its analysis will appear here.</p>
          <button className="btn-primary" onClick={() => navigate("/")}>Analyse a posting</button>
        </div>
      </div>
    );
  }

  const isFraudulent = result.label === "fraudulent";
  const tone = isFraudulent ? "fraud" : "legit";
  const confidencePct = Math.round(result.confidence_score * 100);
  const features = result.explainability_report?.top_features ?? [];

  return (
    <div className="page">
      <button className="back-link" onClick={() => navigate("/")}>
        <ArrowLeftIcon size={16} /> Analyse another posting
      </button>

      <section className={`verdict-card verdict-${tone}`}>
        <div className="verdict-main">
          <span className="verdict-icon">
            {isFraudulent ? <AlertIcon size={28} /> : <CheckIcon size={28} />}
          </span>
          <div>
            <p className="verdict-kicker">HireGuard verdict</p>
            <h2>{isFraudulent ? "Likely fraudulent" : "Likely legitimate"}</h2>
            <p className="verdict-summary">
              {isFraudulent
                ? result.explainability_report?.summary ?? "This posting shows patterns common in recruitment scams."
                : "We didn't find the writing patterns typically seen in scam postings."}
            </p>
          </div>
        </div>
        <ConfidenceRing value={confidencePct} tone={tone} />
      </section>

      {result.is_stub_model && (
        <p className="stub-notice">
          <InfoIcon size={16} />
          <span>
            <strong>Preview mode.</strong> This result comes from a placeholder rule, not the
            trained Random Forest model. Training hasn't been completed yet.
          </span>
        </p>
      )}

      <div className="results-grid">
        {features.length > 0 && (
          <section className="card">
            <h3 className="card-title">Why was this flagged?</h3>
            <ul className="signal-list">
              {features.map((f, i) => (
                <li key={i} className="signal-row">
                  <div className="signal-text">
                    <span>{f.description}</span>
                    <span className={`impact-badge impact-${f.impact}`}>
                      {f.impact === "high" ? "High impact" : "Moderate impact"}
                    </span>
                  </div>
                  <div className="signal-bar">
                    <span className={`signal-fill fill-${f.impact}`} />
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className={`card tips-card tips-${tone}`}>
          <h3 className="card-title">{isFraudulent ? "Protect yourself" : "Stay safe anyway"}</h3>
          <ul className="tip-list">
            {(isFraudulent ? FRAUD_TIPS : LEGIT_TIPS).map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        </section>
      </div>

      {postingText && (
        <details className="card posting-preview">
          <summary>View the posting you submitted</summary>
          <p>{postingText}</p>
        </details>
      )}

      <div className="results-actions">
        <button className="btn-primary" onClick={() => navigate("/")}>Analyse another</button>
        <button className="btn-outline-danger"><FlagIcon size={16} /> Report this posting</button>
      </div>
    </div>
  );
}
