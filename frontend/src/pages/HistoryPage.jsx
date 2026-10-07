import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory } from "../api/client";
import { ArrowLeftIcon, ArrowRightIcon, ClockIcon } from "../components/Icons";

const PLACEHOLDER_USER_ID = "demo-user"; // TODO: replace once auth is built

function VerdictPill({ label }) {
  if (!label) return <span className="pill pill-neutral">Pending</span>;
  const isFraud = label === "fraudulent";
  return (
    <span className={`pill ${isFraud ? "pill-fraud" : "pill-legit"}`}>
      <span className="pill-dot" />
      {isFraud ? "Fraudulent" : "Legitimate"}
    </span>
  );
}

export default function HistoryPage() {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    getHistory({ userId: PLACEHOLDER_USER_ID, page })
      .then((data) => {
        if (cancelled) return;
        setItems(data.items);
        setTotalPages(data.total_pages || 1);
        setTotalItems(data.total_items || 0);
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load submission history. Is the backend running?");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, [page]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Submission history</h1>
          <p className="page-subtitle">
            {totalItems > 0
              ? `${totalItems} posting${totalItems === 1 ? "" : "s"} analysed so far`
              : "Every posting you analyse is listed here."}
          </p>
        </div>
        <Link to="/" className="btn-primary">Analyse a posting</Link>
      </div>

      {error && <p className="error-text" role="alert">{error}</p>}

      {isLoading && (
        <div className="card table-card">
          {[0, 1, 2].map((i) => <div key={i} className="skeleton-row" />)}
        </div>
      )}

      {!isLoading && !error && items.length === 0 && (
        <div className="card empty-state">
          <span className="empty-icon"><ClockIcon size={26} /></span>
          <h2>No submissions yet</h2>
          <p>Postings you analyse will show up here so you can revisit the verdicts.</p>
          <Link to="/" className="btn-primary">Analyse your first posting</Link>
        </div>
      )}

      {!isLoading && !error && items.length > 0 && (
        <>
          <div className="card table-card">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Posting</th>
                  <th>Source</th>
                  <th>Date</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.posting_id}>
                    <td className="cell-title" data-label="Posting">
                      {/* the API truncates raw_text to 60 chars */}
                      {item.title_snippet}{item.title_snippet.length >= 60 ? "…" : ""}
                    </td>
                    <td data-label="Source"><span className="source-tag">{item.source_platform || "-"}</span></td>
                    <td data-label="Date" className="cell-muted">
                      {new Date(item.submitted_at).toLocaleDateString(undefined, {
                        day: "numeric", month: "short", year: "numeric",
                      })}
                    </td>
                    <td data-label="Verdict"><VerdictPill label={item.label} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <span className="cell-muted">Page {page} of {totalPages}</span>
              <div className="pagination-buttons">
                <button
                  className="btn-outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  <ArrowLeftIcon size={16} /> Prev
                </button>
                <button
                  className="btn-outline"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next <ArrowRightIcon size={16} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
