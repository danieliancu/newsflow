import React, { useState, useEffect } from "react";

const TimeAgo = ({ date, source, selectedSource, archived }) => {
  // Dacă articolul este arhivat, afișăm data absolută cu numele lunii (ex: "29 martie 2025")
  if (archived) {
    const formattedDate = new Date(date).toLocaleDateString("ro-RO", {
      day: "2-digit",
      month: "long", // Afișează numele lunii, de exemplu "martie"
      year: "numeric",
    });
    return (
      <span>
        {formattedDate}
        <span className="bumb">&#8226;</span>
        {selectedSource === "all" && (
          <strong className="news-source">{source}</strong>
        )}
      </span>
    );
  }

  const [timeAgo, setTimeAgo] = useState("");

  useEffect(() => {
    const update = () => {
      setTimeAgo(getTimeAgo(date));
    };

    update(); // Inițializare la montare
    const interval = setInterval(update, 60000); // Actualizare la fiecare 60 secunde

    return () => clearInterval(interval); // Curățare la demontare
  }, [date]);

  const getTimeAgo = (date) => {
    const now = new Date();
    const pastDate = new Date(date);
    const diffMs = now - pastDate;
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes === 0) return "Chiar acum";
    if (diffMinutes === 1) return "Acum 1 minut";

    const needsDe = (num) => num >= 20;

    // Dacă este sub 60 de minute, menținem "Acum"
    if (diffMinutes < 60)
      return `Acum ${diffMinutes} ${needsDe(diffMinutes) ? "de " : ""}minute`;

    // Dacă este cel puțin o oră, nu mai adăugăm "Acum"
    const hours = Math.floor(diffMinutes / 60);
    const minutes = diffMinutes % 60;

    const hourText =
      hours === 1 ? "O oră" : hours === 2 ? "Două ore" : `${hours} ore`;

    const minuteText =
      minutes === 0 ? "" : `${minutes} ${needsDe(minutes) ? "de " : ""}minute`;

    return `${hourText}${minuteText ? ` și ${minuteText}` : ""}`;
  };

  return (
    <span>
      {timeAgo}
      <span className="bumb">&#8226;</span>
      {selectedSource === "all" && (
        <strong className="news-source">{source}</strong>
      )}
    </span>
  );
};

export default TimeAgo;
