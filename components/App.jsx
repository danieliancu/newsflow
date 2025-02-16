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

  // Stări pentru filtrele suplimentare din Submenu (ca array-uri)
  const [submenuSourceFilters, setSubmenuSourceFilters] = useState([]);
  const [submenuLabelFilters, setSubmenuLabelFilters] = useState([]);
  // Obiect care memorează filtrele pentru fiecare categorie
  const [filtersByCategory, setFiltersByCategory] = useState({});
  const [isSubmenuPanelOpen, setIsSubmenuPanelOpen] = useState(false);

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

  // Actualizează filtrele locale din Submenu când se schimbă categoria,
  // folosind valorile memorate în filtersByCategory (dacă există)
  useEffect(() => {
    if (filtersByCategory[selectedCategory]) {
      setSubmenuSourceFilters(filtersByCategory[selectedCategory].sourceFilters);
      setSubmenuLabelFilters(filtersByCategory[selectedCategory].labelFilters);
    } else {
      setSubmenuSourceFilters([]);
      setSubmenuLabelFilters([]);
    }
  }, [selectedCategory, filtersByCategory]);

  const handleFilter = (source) => {
    setSelectedSource(source);
    filterData(source, selectedCategory);
  };

  const handleCategoryFilter = (category) => {
    // Nu resetăm căutarea la schimbarea categoriei, pentru a păstra rezultatele vechi
    setSubmittedSearchTerm("");
    setSelectedCategory(category);
    setSelectedSource("all");
    filterData("all", category);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const filterData = (source, category) => {
    if (!allData.length) return;
    let filtered = [...allData];
    if (source !== "all") {
      filtered = filtered.filter((item) => item.source === source);
    }
    if (category) {
      filtered = filtered.filter((item) => item.cat === category);
    }
    setFilteredData(filtered);
  };

  // Aplicăm filtrele suplimentare din Submenu la datele filtrate deja
  const finalFilteredData = useMemo(() => {
    let data = [...filteredData];
    if (submenuSourceFilters.length > 0) {
      data = data.filter((item) => submenuSourceFilters.includes(item.source));
    }
    if (submenuLabelFilters.length > 0) {
      data = data.filter((item) => submenuLabelFilters.includes(item.label));
    }
    return data;
  }, [filteredData, submenuSourceFilters, submenuLabelFilters]);

  // Funcție de sortare comună pentru articole
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
    const data = finalFilteredData.filter(
      (item) => item.imgSrc && item.cat === selectedCategory
    );
    return sortData(data);
  }, [finalFilteredData, selectedCategory, selectedSort]);

  const textNews = useMemo(() => {
    const data = finalFilteredData.filter(
      (item) => !item.imgSrc && item.cat === selectedCategory
    );
    return sortData(data);
  }, [finalFilteredData, selectedCategory, selectedSort]);

  // Sursele și etichetele disponibile pentru categoria selectată
  const availableSourcesForCategory = Array.from(
    new Set(allData.filter(item => item.cat === selectedCategory).map(item => item.source))
  );
  const availableLabelsForCategory = Array.from(
    new Set(allData.filter(item => item.cat === selectedCategory).map(item => item.label))
  );

  // Funcții pentru actualizarea filtrelor pentru categoria curentă
  const updateSourceFilters = (newSourceFilters) => {
    setSubmenuSourceFilters(newSourceFilters);
    setFiltersByCategory((prev) => ({
      ...prev,
      [selectedCategory]: {
        sourceFilters: newSourceFilters,
        labelFilters: submenuLabelFilters,
      },
    }));
  };

  const updateLabelFilters = (newLabelFilters) => {
    setSubmenuLabelFilters(newLabelFilters);
    setFiltersByCategory((prev) => ({
      ...prev,
      [selectedCategory]: {
        sourceFilters: submenuSourceFilters,
        labelFilters: newLabelFilters,
      },
    }));
  };

  // Funcția de resetare completă a filtrelor pentru categoria curentă
  const resetFilters = () => {
    setSubmenuSourceFilters([]);
    setSubmenuLabelFilters([]);
    setFiltersByCategory((prev) => ({
      ...prev,
      [selectedCategory]: { sourceFilters: [], labelFilters: [] },
    }));
  };

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

      {!isSearching && (
        <Submenu
          selectedSort={selectedSort}
          onSortChange={setSelectedSort}
          availableSources={availableSourcesForCategory}
          availableLabels={availableLabelsForCategory}
          isPanelOpen={isSubmenuPanelOpen}
          openPanel={() => setIsSubmenuPanelOpen(true)}
          closePanel={() => setIsSubmenuPanelOpen(false)}
          submenuSourceFilters={submenuSourceFilters}
          onSourceFilterChange={updateSourceFilters}
          submenuLabelFilters={submenuLabelFilters}
          onLabelFilterChange={updateLabelFilters}
          onResetFilters={resetFilters}
        />
      )}

      {loading ? (
        <div>
          <div className="loading">
            <div className="spinner"></div>
          </div>
          <p style={{ textAlign:"center", color:"var(--red)", padding:"20px", fontWeight:"bold"}}>
            Se încarcă ultimele știri
          </p>
        </div>
      ) : submittedSearchTerm.trim() ? (
        <SearchResults searchTerm={submittedSearchTerm} allData={allData} />
      ) : (
        <div className="container grid-layout">
          {sortedImageNews.length === 0 ? (
            <p style={{ textAlign: "center", fontWeight: "bold", padding: "20px" }}>
              Nu s-a găsit nicio știre pentru acest filtru
            </p>
          ) : sortedImageNews.length >= 5 ? (
            <>
              <Carousel key={selectedSource} items={sortedImageNews.slice(0, 4)} />
              {sortedImageNews.slice(4).map((item, index) => (
                <div className="container-news" key={index}>
                  <div className="container-news-image">
                    <p className="label">{item.label}</p>
                    <img src={item.imgSrc} alt={item.text || "Image"} className="news-image" />
                  </div>
                  {item.href && (
                    <a href={item.href} target="_blank" rel="noopener noreferrer">
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
                  )}
                </div>
              ))}
            </>
          ) : (
            sortedImageNews.map((item, index) => (
              <div className="container-news" key={index}>
                <div className="container-news-image">
                  <p className="label">{item.label}</p>
                  <img src={item.imgSrc} alt={item.text || "Image"} className="news-image" />
                </div>
                {item.href && (
                  <a href={item.href} target="_blank" rel="noopener noreferrer">
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
                )}
              </div>
            ))
          )}
        </div>
      )}

      <ScrollToTop />
      {!loading && <Footer />}
      <Analytics />
    </div>
  );
};

export default App;
