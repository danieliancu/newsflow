import React from "react";
import ScrollToTop from "./ScrollToTop"; // ✅ Import nou
import { FaCaretRight } from "react-icons/fa"; // ✅ Iconiță pentru titluri de categorie

// Funcția de eliminare a diacriticelor românești
function removeRomanianDiacritics(str) {
  return str
    .replace(/[ăĂ]/g, "a")
    .replace(/[âÂ]/g, "a")
    .replace(/[îÎ]/g, "i")
    .replace(/[șȘ]/g, "s")
    .replace(/[țȚ]/g, "t");
}

// Funcția de căutare inteligentă
const SearchResults = ({ searchTerm, allData }) => {
  console.log("SearchResults", searchTerm, allData);

  if (!searchTerm.trim()) return null; // Dacă inputul e gol, nu afișăm nimic

  // 1) Normalizăm "searchTerm" (fără diacritice + lowercase)
  const normalizedSearchTerm = removeRomanianDiacritics(searchTerm.toLowerCase());

  // 2) Separăm termenul de căutare în cuvinte (ex: "trumps news" -> ["trumps", "news"])
  const searchWords = normalizedSearchTerm.split(/\s+/); // Split pe spații multiple

  // 3) Aplicăm filtrarea avansată
  const filteredSearch = allData.filter((item) => {
    // Normalizăm textul articolului
    const normalizedText = removeRomanianDiacritics(item.text.toLowerCase());

    // Separăm articolul în cuvinte (ex: "Donald Trump wins" -> ["donald", "trump", "wins"])
    const articleWords = normalizedText.split(/\s+/);

    // 4) Verificăm dacă ORICE cuvânt din searchTerm există în ORICE cuvânt din articol
    return searchWords.some((searchWord) =>
      articleWords.some((articleWord) => articleWord.startsWith(searchWord))
    );
  });

  // Dacă nu există rezultate
  if (filteredSearch.length === 0) {
    return (
      <h2 className="no-results">
        Nu am găsit nimic pentru <strong>{searchTerm}</strong>.
      </h2>
    );
  }

  // 📌 Grupăm rezultatele după categorie (cat)
  const groupedResults = filteredSearch.reduce((acc, item) => {
    if (!acc[item.cat]) {
      acc[item.cat] = [];
    }
    acc[item.cat].push(item);
    return acc;
  }, {});

  // Afișăm rezultatele grupate pe categorii
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