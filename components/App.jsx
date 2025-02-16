import React, { useState, useEffect, useMemo } from "react";
import { FaCaretRight } from "react-icons/fa";
import { Analytics } from "@vercel/analytics/react";

import Carousel from "./Carousel";
import Menu from "./Menu";
import Top from "./Top";
import Footer from "./Footer";
import SearchResults from "./SearchResults";
import ScrollToTop from "./ScrollToTop";
import TimeAgo from "./TimeAgo";
import Submenu from "./Submenu";

const App = () => {
  const [allData, setAllData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [submittedSearchTerm, setSubmittedSearchTerm] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [selectedSource, setSelectedSource] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("Actualitate");
  const [loading, setLoading] = useState(true);
  const [selectedSort, setSelectedSort] = useState("Cele mai noi");

  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true);
      try {
        const response = await fetch("/api/articles");
        const result = await response.json();
        if (response.ok) {
          setAllData(result.data);
          setFilteredData(result.data);
        } else {
          setError(result.error || "Failed to fetch data");
        }
      } catch {
        setError("Request failed");
      } finally {
        setLoading(false);
      }
    };
    fetchAllData();
  }, []);

  const handleFilter = (source) => {
    setSelectedSource(source);
    filterData(source, selectedCategory);
  };

  const handleCategoryFilter = (category) => {
    setIsSearching(false);
    setSubmittedSearchTerm("");
    setSelectedCategory(category);
    setSelectedSource("all");
    filterData("all", category);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const filterData = (source, category) => {
    if (!allData.length) return;
    let filtered = [...allData];
    if (source !== "all") filtered = filtered.filter((item) => item.source === source);
    if (category) filtered = filtered.filter((item) => item.cat === category);
    setFilteredData(filtered);
  };

  // Functie de sortare comună pentru ambele categorii de știri
  const sortData = (data) => {
    const sorted = [...data];
    switch (selectedSort) {
      case "Cele mai noi":
        sorted.sort((a, b) => new Date(b.date) - new Date(a.date));
        break;
      case "Cele mai vechi":
        sorted.sort((a, b) => new Date(a.date) - new Date(b.date));
        break;
      case "Alfabetic A-Z":
        sorted.sort((a, b) => a.text.localeCompare(b.text));
        break;
      case "Alfabetic Z-A":
        sorted.sort((a, b) => b.text.localeCompare(a.text));
        break;
      default:
        sorted.sort((a, b) => new Date(b.date) - new Date(a.date));
    }
    return sorted;
  };

  const sortedImageNews = useMemo(() => {
    const data = filteredData.filter((item) => item.imgSrc && item.cat === selectedCategory);
    return sortData(data);
  }, [filteredData, selectedCategory, selectedSort]);

  const textNews = useMemo(() => {
    const data = filteredData.filter((item) => !item.imgSrc && item.cat === selectedCategory);
    return sortData(data);
  }, [filteredData, selectedCategory, selectedSort]);

  return (
    <div>
      <Top
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        setIsSearching={setIsSearching}
        submittedSearchTerm={submittedSearchTerm}
        setSubmittedSearchTerm={setSubmittedSearchTerm}
      />

      <Menu
        selectedSource={selectedSource}
        selectedCategory={selectedCategory}
        handleFilter={handleFilter}
        handleCategoryFilter={handleCategoryFilter}
        availableSources={Array.from(new Set(allData.map((item) => item.source)))}
        availableCategories={Array.from(new Set(allData.map((item) => item.cat)))}
        setSearchTerm={setSearchTerm}
        setIsSearching={setIsSearching}
        setSubmittedSearchTerm={setSubmittedSearchTerm}
      />

      {!isSearching && <Submenu selectedSort={selectedSort} onSortChange={setSelectedSort} />}

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
        </div>
      )}

      {!loading && error && (
        <div style={{ color: "red", textAlign: "center", padding: "20px" }}>
          <h3>Error:</h3>
          <p>{error}</p>
        </div>
      )}

      {!loading && isSearching ? (
        <SearchResults searchTerm={submittedSearchTerm} allData={allData} />
      ) : (
        <div className="container grid-layout">
          {sortedImageNews.length > 4 && (
            <Carousel key={selectedSource} items={sortedImageNews.slice(0, 4)} />
          )}

          {loading ? (
            <span
              style={{
                textAlign: "center",
                width: "100%",
                display: "inline-block",
                color: "var(--red)",
                paddingBottom: "20px",
                fontSize: "14px",
                fontWeight: "bold",
              }}
            >
              SE ÎNCARCĂ ULTIMELE ȘTIRI...
            </span>
          ) : (
            <p className="ultimele">
              Ultimele știri din {selectedCategory} <FaCaretRight style={{ display: "inline-block" }} />
            </p>
          )}

          {sortedImageNews.slice(4).map((item, index) => (
            <div className="container-news" key={index}>
              <div className="container-news-image">
                <p className="label">{item.label}</p>
                <img src={item.imgSrc} alt={item.text || "Image"} className="news-image" />
              </div>
              {item.href && (
                <a href={item.href} target="_blank" rel="noopener noreferrer">
                  <h3><span className="labelMobil">{item.label}.</span> {item.text}</h3>
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
              )}
            </div>
          ))}
        </div>
      )}

      <ScrollToTop />
      {!loading && <Footer />}
      <Analytics />
    </div>
  );
};

export default App;
