import React from "react";

const Footer = () => {
  return (
    <footer className="footer" id="footer">
      <div className="footer-container">
        <div className="footer-columns">
          <div className="footer-column">
            <h3>NEWSFLOW</h3>
            <ul>
              <li><a href="/despre">Despre noi</a></li>
              <li><a href="/contact">Contact</a></li>
            </ul>
          </div>

          <div className="footer-column">
            <h3>COLABORARE</h3>
            <ul>
              <li><a href="/publicitate">Publicitate</a></li>
              <li><a href="/reteaua-publicitati">Rețeaua de publicații</a></li>
            </ul>
          </div>

          <div className="footer-column">
            <h3>LEGAL</h3>
            <ul>
              <li><a href="/privacy-policy">Privacy Policy</a></li>
              <li><a href="/cookie-policy">Cookie Policy</a></li>
              <li><a href="/legal-notice">Legal Notice</a></li>
              <li><a href="/privacy-settings">Privacy Settings</a></li>
            </ul>
          </div>

          <div className="footer-column newsletter">
            <h3>NEWSLETTER</h3>
            <p>
              Completează câmpul de mai jos cu adresa ta de email și vei primi newsletter cu ultimele știri, personalizat cu preferințele tale.
            </p>
            <input type="email" placeholder="Adresa de email" />
            <button>Vreau să primesc newsletter!</button>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
