import React from "react";
import TimeAgo from "./TimeAgo";

const NewsCard = ({ item, selectedSource }) => {
  return (
    <div className="container-news" key={item.id}>
      {/* 🖼️ Imagine și Etichetă */}
      {item.imgSrc && (
        <div className="container-news-image">
          <p className="label">{item.label}</p>
          <img
            src={item.imgSrc}
            alt={item.text || "Image"}
            className="news-image"
          />
        </div>
      )}

      {/* 📝 Titlu și Link */}
      {item.href && (
        <a href={item.href} target="_blank" rel="noopener noreferrer">
          <h3>
            <span className="labelMobil">{item.label}.</span> {item.text}
          </h3>
          {/* ⏱️ Timp relativ */}
          <p className="ago">
            <TimeAgo
              date={item.date}
              source={item.source}
              selectedSource={selectedSource}
            />
          </p>
          {/* 📰 Suprapunere stilizată (opțional) */}
          <div className="supra" style={{ border: ".5px solid black" }}>
            <TimeAgo
              date={item.date}
              source={item.source}
              selectedSource={selectedSource}
            />
          </div>
        </a>
      )}
    </div>
  );
};

export default NewsCard;
