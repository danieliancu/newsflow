import React from "react";

const TimeAgo = ({ date, source, selectedSource }) => {
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
      {getTimeAgo(date)}
      <span className="bumb">&#8226;</span>
      {selectedSource === "all" && <strong className="news-source">{source}</strong>}
    </span>
  );
};

export default TimeAgo;
