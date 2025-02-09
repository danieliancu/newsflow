import React, { useState, useEffect, useMemo } from "react";
import Carousel from "./Carousel";
import Menu from "./Menu";
import Top from "./Top";
import Footer from "./Footer";
import { FaToggleOn, FaToggleOff, FaCaretRight } from "react-icons/fa";
import { Analytics } from "@vercel/analytics/react";
import SearchResults from "./SearchResults";
import ScrollToTop from "./ScrollToTop";
import TimeAgo from "./TimeAgo";

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
  const [isAutoplay, setIsAutoplay] = useState(true);
  


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

  useEffect(() => {
    let intervalId;
    if (isAutoplay && window.innerWidth >= 600) {
      intervalId = setInterval(() => {
        const container = document.querySelector(".news-item-container");
        if (container) {
          const currentTop = parseInt(container.style.top || "0", 10);
          container.style.top = `${currentTop - 1}px`;
        }
      }, 50);
    }
    return () => clearInterval(intervalId);
  }, [isAutoplay]);

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

  const sortedImageNews = useMemo(() => {
    return filteredData
      .filter((item) => item.imgSrc)
      .sort((a, b) => new Date(b.date) - new Date(a.date));
  }, [filteredData]);

  const textNews = useMemo(() => {
    return filteredData
      .filter((item) => !item.imgSrc)
      .sort((a, b) => new Date(b.date) - new Date(a.date));
  }, [filteredData]);

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
          {sortedImageNews.length > 4 && <Carousel key={selectedSource} items={sortedImageNews.slice(0, 4)} />}

          {textNews.length > 8 && (
            <>
              <p className="peScurt">
                PE SCURT <FaCaretRight style={{ display:"inline-block" }} />
              </p>
              <div className="container-news container-news-no-img">
                <div className="container-news-no-img-top">
                  <span className="top-top">
                    <span style={{ color: "#d80000" }}>pe scurt</span>
                    <span onClick={() => setIsAutoplay(!isAutoplay)} style={{ cursor: "pointer", marginLeft: "10px" }}>
                      autoplay {isAutoplay ? <FaToggleOn style={{ display:"inline-block", verticalAlign:"text-top" }} /> : <FaToggleOff style={{ color: "grey", display:"inline-block", verticalAlign:"text-top" }} />}
                    </span>
                  </span>
                </div>

                <div className="news-item-container show-items">
                  {textNews.map((item, index) => (
                    <div className="news-item" key={index} style={{ borderLeft: ".5px solid #d80000" }}>
                      <span className="bumb bumbSpecial">&#8226;</span>
                      <span className="news-item-border">
                        <p className="ago">
                          <TimeAgo date={item.date} source={item.source} selectedSource={selectedSource} />
                        </p>
                      </span>
                      {item.href && (
                        <a href={item.href} target="_blank" rel="noopener noreferrer">
                          <h3>{item.text}</h3>
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
{loading ? (
  <span style={{ textAlign:"center", width:"100%", display:"inline-block", color:"var(--red)", paddingBottom:"20px", fontSize:"14px", fontWeight:"bold" }}>
    SE ÎNCARCĂ ULTIMELE ȘTIRI...
  </span>
) : (
  <p className="ultimele">
    ULTIMELE ȘTIRI <FaCaretRight style={{ display:"inline-block" }} />
  </p>
)}

          {sortedImageNews.slice(4).map((item, index) => (
            <div className="container-news" key={index}>
              <img src={item.imgSrc} alt={item.text || "Image"} className="news-image" />
              {item.href && (
                <a href={item.href} target="_blank" rel="noopener noreferrer">
                  <p className="ago">
                    <TimeAgo date={item.date} source={item.source} selectedSource={selectedSource} />
                  </p>

                  <div className="supra" style={{ border: ".5px solid black" }}>
                    <TimeAgo date={item.date} source={item.source} selectedSource={selectedSource} />
                  </div>
                  <h3>{item.text}</h3>
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
