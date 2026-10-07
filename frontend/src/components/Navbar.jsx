import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">HireGuard</Link>
      <div className="navbar-links">
        <Link to="/history">History</Link>
        <a href="#logout">Log Out</a>
      </div>
    </nav>
  );
}
