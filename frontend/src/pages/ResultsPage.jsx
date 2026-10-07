import { useLocation, useNavigate } from "react-router-dom";

export default function ResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result;

  if (!result) {
    // Direct navigation to /results with no state -- send them back to submit one.
    return (
      <div className="page">
        <p>No classification result to show. Please submit a posting first.</p>
        <button className="btn-secondary" onClick={() => navigate("/")}>
          Go to Submission Page
        </button>
      </div>
    );
  }

  const isFraudulent = result.label === "fraudulent";
  const confidencePct = Math.round(result.confidence_score * 100);

  return (
    <div className="page">
      <div className={`verdict-card ${isFraudulent ? "verdict-fraud" : "verdict-legit"}`}>
        <span className="verdict-icon">{isFraudulent ? "!" : "✓"}</span>
        <div>
          <h2>{isFraudulent ? "Likely Fraudulent" : "Likely Legitimate"}</h2>
          <p>Confidence score: {confidencePct}%</p>
        </div>
      </div>

      {result.is_stub_model && (
        <p className="stub-notice">
          Note: this result was produced by a placeholder rule, not the trained Random Forest
          model -- training hasn't been completed yet.
        </p>
      )}

      {result.explainability_report && (
        <>
          <h3>Why was this flagged?</h3>
          <ul className="shap-feature-list">
            {result.explainability_report.top_features.map((f, i) => (
              <li key={i} className="shap-feature-row">
                <span>{f.description}</span>
                <span className={`impact-badge impact-${f.impact}`}>
                  {f.impact === "high" ? "High impact" : "Moderate impact"}
                </span>
              </li>
            ))}
          </ul>

          <div className="recommendation-panel">
            <strong>Recommendation</strong>
            <p>
              Do not share personal or financial information. Verify the company independently
              before applying.
            </p>
          </div>
        </>
      )}

      <div className="results-actions">
        <button className="btn-outline" onClick={() => navigate("/")}>
          Analyse Another
        </button>
        <button className="btn-outline-danger">Report This Posting</button>
      </div>
    </div>
  );
}
