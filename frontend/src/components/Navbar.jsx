import { Link, NavLink } from "react-router-dom";
import { ShieldIcon } from "./Icons";

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          <span className="brand-mark"><ShieldIcon size={18} /></span>
          HireGuard
        </Link>
        <nav className="navbar-links">
          <NavLink to="/" end>Analyse</NavLink>
          <NavLink to="/history">History</NavLink>
          <a href="#logout" className="navbar-logout">Log Out</a>
        </nav>
      </div>
    </header>
  );
}
