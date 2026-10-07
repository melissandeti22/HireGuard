import { useEffect, useState } from "react";
import { getHistory } from "../api/client";

const PLACEHOLDER_USER_ID = "demo-user"; // TODO: replace once auth is built

export default function HistoryPage() {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
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
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load submission history.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, [page]);

  return (
    <div className="page">
      <h1>Submission History</h1>

      {isLoading && <p>Loading...</p>}
      {error && <p className="error-text">{error}</p>}

      {!isLoading && !error && (
        <>
          <table className="history-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Source</th>
                <th>Date</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.posting_id}>
                  <td>{item.title_snippet}</td>
                  <td>{item.source_platform}</td>
                  <td>{new Date(item.submitted_at).toLocaleDateString()}</td>
                  <td>
                    <span className={`impact-badge impact-${item.label === "fraudulent" ? "high" : "legit"}`}>
                      {item.label === "fraudulent" ? "Fraudulent" : "Legitimate"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination">
            <span>Page {page} of {totalPages}</span>
            <div>
              <button
                className="btn-outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Prev
              </button>
              <button
                className="btn-outline"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
