import React, { useState } from "react";
import Modal from "./Modal";

const Footer = () => {
  const [email, setEmail] = useState("");
  const [modalMessage, setModalMessage] = useState("");
  const [showModal, setShowModal] = useState(false);

  const handleNewsletterSubmit = async () => {
    if (!email) {
      setModalMessage("Te rugăm să introduci o adresă de email.");
      return setShowModal(true);
    }

    try {
      const response = await fetch("/api/newsletter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();

      if (response.ok) {
        setModalMessage(
          data.exists
            ? "Emailul există deja în baza noastră de date!"
            : "Vă mulțumim pentru înregistrare!"
        );
        setEmail("");
      } else {
        setModalMessage("Eroare la abonare. Încearcă din nou.");
      }
    } catch (error) {
      console.error("Eroare la trimiterea datelor:", error);
      setModalMessage("A apărut o eroare. Încearcă din nou.");
    } finally {
      setShowModal(true);
    }
  };

  return (
    <>
      <footer className="footer" id="footer">
        <div className="footer-container">
          <div className="footer-columns">
            <div className="footer-column">
              <h3>NEWSFLOW</h3>
              <ul>
                <li>
                  <a href="/despre">Despre noi</a>
                </li>
                <li>
                  <a href="/contact">Contact</a>
                </li>
              </ul>
            </div>

            <div className="footer-column">
              <h3>COLABORARE</h3>
              <ul>
                <li>
                  <a href="/publicitate">Publicitate</a>
                </li>
                <li>
                  <a href="/reteaua-publicitati">Rețeaua de publicații</a>
                </li>
              </ul>
            </div>

            <div className="footer-column">
              <h3>LEGAL</h3>
              <ul>
                <li>
                  <a href="/privacy-policy">Privacy Policy</a>
                </li>
                <li>
                  <a href="/cookie-policy">Cookie Policy</a>
                </li>
                <li>
                  <a href="/legal-notice">Legal Notice</a>
                </li>
                <li>
                  <a href="/privacy-settings">Privacy Settings</a>
                </li>
              </ul>
            </div>

            <div className="footer-column newsletter">
              <h3>NEWSLETTER</h3>
              <p>
                Completează câmpul de mai jos cu adresa ta de email și vei primi
                newsletter cu ultimele știri, personalizat cu preferințele tale.
              </p>
              <input
                type="email"
                placeholder="Adresa de email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <button
                className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                onClick={handleNewsletterSubmit}
              >
                Vreau să primesc newsletter!
              </button>
            </div>
          </div>
        </div>
      </footer>

      {showModal && (
        <Modal
          message={modalMessage}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
};

export default Footer;
