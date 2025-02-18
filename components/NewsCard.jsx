import React from "react";
import Link from "next/link";
import TimeAgo from "./TimeAgo";

const NewsCard = ({ item, selectedSource }) => {
  // Generăm un slug SEO-friendly din textul știrii
  const slug =
    item.text
      ?.toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "stire";

  return (
    <div className="container-news" key={item.id}>
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

     { /* <Link legacyBehavior href={`/news/${slug}-${item.id}`}>  */}
        <a href={item.href}>
          <h3>
            <span className="labelMobil">{item.label}.</span> {item.text}
          </h3>
          <p className="ago">
            <TimeAgo
              date={item.date}
              source={item.source}
              selectedSource={selectedSource}
            />
          </p>
          <div className="supra" style={{ border: ".5px solid black" }}>
            <TimeAgo
              date={item.date}
              source={item.source}
              selectedSource={selectedSource}
            />
          </div>
        </a>
      { /* </Link> */} 
    </div>
  );
};

export default NewsCard;
