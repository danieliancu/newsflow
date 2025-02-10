import React, { useState, useEffect } from "react";

const TimeAgo = ({ date, source, selectedSource }) => {
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

    if (diffMinutes < 60) 
      return `Acum ${diffMinutes} ${needsDe(diffMinutes) ? "de " : ""}minute`;

    const hours = Math.floor(diffMinutes / 60);
    const minutes = diffMinutes % 60;

    const hourText =
      hours === 1 ? "o oră" : hours === 2 ? "două ore" : `${hours} ore`;

    const minuteText = minutes === 0 
      ? "" 
      : `${minutes} ${needsDe(minutes) ? "de " : ""}minute`;

    return `Acum ${hourText}${minuteText ? ` și ${minuteText}` : ""}`;
  };

  return (
    <span>
      {timeAgo}
      <span className="bumb">&#8226;</span>
      {selectedSource === "all" && <strong className="news-source">{source}</strong>}
    </span>
  );
};

export default TimeAgo;
