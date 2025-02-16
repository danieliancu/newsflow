import React from "react";
import ScrollToTop from "./ScrollToTop";
import { FaCaretRight } from "react-icons/fa";

function removeRomanianDiacritics(str) {
  return str
    .replace(/[ăĂ]/g, "a")
    .replace(/[âÂ]/g, "a")
    .replace(/[îÎ]/g, "i")
    .replace(/[șȘ]/g, "s")
    .replace(/[țȚ]/g, "t");
}

const SearchResults = ({ searchTerm, allData }) => {
  console.log("SearchResults", searchTerm, allData);

  if (!searchTerm.trim()) return null;

  const normalizedSearchTerm = removeRomanianDiacritics(searchTerm.toLowerCase());
  const searchWords = normalizedSearchTerm.split(/\s+/);

  const filteredSearch = allData.filter((item) => {
    const normalizedText = removeRomanianDiacritics(item.text.toLowerCase());
    const articleWords = normalizedText.split(/\s+/);
    return searchWords.some((searchWord) =>
      articleWords.some((articleWord) => articleWord.includes(searchWord))
    );
  });

  if (filteredSearch.length === 0) {
    return (
      <h2 className="no-results">
        Nu am găsit nimic pentru <strong>{searchTerm}</strong>.
      </h2>
    );
  }

  const groupedResults = filteredSearch.reduce((acc, item) => {
    if (!acc[item.cat]) {
      acc[item.cat] = [];
    }
    acc[item.cat].push(item);
    return acc;
  }, {});

  return (
    <div className="search-results">
      <h1>
        Cuvânt căutat: <strong>{searchTerm}</strong>
      </h1>

      {Object.keys(groupedResults).map((category) => (
        <div key={category}>
          <p className="catSearch">
            {category} <FaCaretRight style={{ display: "inline-block" }} />
          </p>
          <div className="results-grid" style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {groupedResults[category].map((item, index) => (
              <div className="container-news" key={index}>
                {item.imgSrc && (
                  <div className="searchImg">
                    <img alt={item.text || "No title"} className="news-image" src={item.imgSrc} />
                  </div>
                )}
                {item.href && (
                  <a href={item.href} target="_blank" rel="noopener noreferrer">
                    <p className="ago">
                      <strong className="news-source">{item.source}</strong>
                    </p>
                    <h3>{item.text}</h3>
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      <ScrollToTop />
    </div>
  );
};

export default SearchResults;
