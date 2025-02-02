import React, { useState, useEffect } from "react";
import Carousel from "./Carousel";
import Menu from "./Menu";
import Top from "./Top";
import Footer from "./Footer";
import { FaToggleOn, FaToggleOff, FaSync } from "react-icons/fa";

const App = () => {
  const [allData, setAllData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [error, setError] = useState("");
  const [selectedSource, setSelectedSource] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("Actualitate"); // Implicit "Actualitate"
  const [loading, setLoading] = useState(true);
  const [isRotated, setIsRotated] = useState(false); // Stare pentru rotația SVG-ului
  const [showScrollTop, setShowScrollTop] = useState(false); // Stare pentru săgeata de scroll-top
  // Starea pentru numărul de articole cu imagine afișate (după cele 4 din Carousel)
  const [visibleImageNewsCount, setVisibleImageNewsCount] = useState(20);
  const [isAutoplay, setIsAutoplay] = useState(true);

  useEffect(() => {
    let intervalId;
  
    if (isAutoplay) {
      intervalId = setInterval(() => {
        const container = document.querySelector('.news-item-container');
        if (container) {
          const currentTop = parseInt(container.style.top || '0', 10);
          container.style.top = `${currentTop - 1}px`;
  
          // Reset
          // if (Math.abs(currentTop) > resetThreshold) {
          //   container.style.top = '0';
          // }
        }
      }, 50); // O ajustare la fiecare 20ms creează o mișcare lină
    }
  
    return () => {
      clearInterval(intervalId);
    };
  }, [isAutoplay]);

  // Funcția de toggle: inversează starea curentă
  const toggleAutoplay = () => {
    setIsAutoplay((prevState) => !prevState);
  };

  // Funcția de reset: readuce containerul cu news-item la poziția inițială
const handleReset = () => {
  // Oprește autoplay-ul
  setIsAutoplay(false);

  const container = document.querySelector('.news-item-container');
  if (container) {
    container.style.top = '0';
  }

  // Pornește din nou autoplay-ul după un scurt delay, pentru a permite resetarea
  setTimeout(() => {
    setIsAutoplay(true);
  }, 100); // delay de 100ms (poți ajusta dacă este necesar)
};

  const handleSvgClick = () => {
    setIsRotated((prev) => !prev); // Inversează starea de rotație
  };

  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true); // Afișează spinnerul
      try {
        const response = await fetch("/api/articles");
        const result = await response.json();

        if (response.ok) {
          setAllData(result.data);
          // Filtrare implicită la încărcare
          filterData("all", "Actualitate", result.data);
        } else {
          setError(result.error || "Failed to fetch data");
        }
      } catch (err) {
        setError("Request failed");
      } finally {
        setLoading(false); // Ascunde spinnerul
      }
    };

    fetchAllData();
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 200) {
        setShowScrollTop(true);
      } else {
        setShowScrollTop(false);
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleScrollTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleFilter = (source) => {
    setSelectedSource(source);
    filterData(source, selectedCategory);
  };

  const handleCategoryFilter = (category) => {
    setSelectedCategory(category);
    setSelectedSource("all"); // Resetează sursa la "all" când se schimbă categoria
    filterData("all", category);
    window.scrollTo({ top: 0, behavior: "smooth" });
    setIsRotated(false); // Resetează rotația SVG-ului
  };

  // Filtrare în funcție de sursă și categorie – se resetează și numărul de articole vizibile
  const filterData = (source, category, data = allData) => {
    let filtered = data;

    if (source !== "all") {
      filtered = filtered.filter((item) => item.source === source);
    }

    if (category) {
      filtered = filtered.filter((item) => item.cat === category);
    }

    setFilteredData(filtered);
    // Resetăm contorul de paginare la fiecare filtrare nouă
    setVisibleImageNewsCount(20);
  };

  const getSourcesForCategory = () => {
    const articlesInCategory = allData.filter((item) => item.cat === selectedCategory);
    const validArticles = articlesInCategory.filter((item) => item.imgSrc);
    const sourceCounts = {};
    validArticles.forEach((item) => {
      sourceCounts[item.source] = (sourceCounts[item.source] || 0) + 1;
    });
    return Object.keys(sourceCounts).filter((source) => sourceCounts[source] >= 5);
  };

  // Handler pentru butonul de "Vezi mai multe stiri"
  const handleLoadMore = () => {
    setVisibleImageNewsCount((prevCount) => prevCount + 20);
  };

  // Calculăm lista articolelor cu imagini și le sortăm descrescător după dată
  const sortedImageNews = filteredData
    .filter((item) => item.imgSrc)
    .sort((a, b) => new Date(b.date) - new Date(a.date));

  return (
    <div>
      <Top />
      <Menu
        selectedSource={selectedSource}
        selectedCategory={selectedCategory}
        handleFilter={handleFilter}
        handleCategoryFilter={handleCategoryFilter}
        availableSources={getSourcesForCategory()}
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
      
      {!loading && filteredData.length > 0 && (
        <div className="container grid-layout">
          {/* Dacă există cel puțin 5 articole cu imagine, afișăm Carousel-ul cu primele 4 */}
          {sortedImageNews.length > 4 && (
            <Carousel key={selectedSource} items={sortedImageNews.slice(0, 4)} />
          )}
          
          {/* Secțiunea pentru articolele fără imagine */}
          {filteredData.filter((item) => !item.imgSrc).length > 0 && (
            <div className="container-news container-news-no-img">
              <div className="container-news-no-img-top">
                <span
                  className="caret-news-top"
                  onClick={handleSvgClick}
                  style={{ cursor: "pointer" }}
                >
                  <svg
                    width="13"
                    height="13"
                    xmlns="http://www.w3.org/2000/svg"
                    className={isRotated ? "rotated" : ""}
                  >
                    <polygon points="6,0 0,12 12,12" fill="white" />
                  </svg>
                  <span
                    style={{
                      fontSize: "14px",
                      textTransform: "lowercase",
                      fontWeight: "lighter",
                      paddingLeft: "5px",
                    }}
                  >
                    Apasă pentru {isRotated ? "a ascunde" : "a vizualiza"} newsflow
                  </span>
                </span>
                
                <span className="top-top">
                  <span style={{ color: "#d80000" }}>newsflow</span>
                  <span
                    onClick={toggleAutoplay}
                    style={{ cursor: "pointer", marginLeft: "10px" }}
                  >
                    autoplay{" "}
                    {isAutoplay ? (
                      <FaToggleOn
                        style={{
                          display: "inline-block",
                          fontSize: "18px",
                          verticalAlign: "bottom",
                        }}
                      />
                    ) : (
                      <FaToggleOff
                        style={{
                          display: "inline-block",
                          fontSize: "18px",
                          verticalAlign: "bottom",
                          color: "grey",
                        }}
                      />
                    )}
                  </span>
                  {/* Butonul de reset */}

                  <span
                    onClick={handleReset}
                    style={{ cursor: "pointer", marginLeft: "10px" }}
                    title="Reset newsflow"
                  >
                    TOP
                    <svg
                    style={{ display: "inline-block", verticalAlign: "text-top" }}
                    width="12"
                    height="12"
                    xmlns="http://www.w3.org/2000/svg"
                    >
                    <polygon points="6,0 0,12 12,12" fill="black" />
                  </svg>
                  </span>
                </span>
              </div>
              
              <div className={`news-item-container ${isRotated ? "show-items" : "hide-items"}`}>
                {filteredData
                  .filter((item) => !item.imgSrc)
                  .sort((a, b) => new Date(b.date) - new Date(a.date))
                  .map((item, index) => (
                    <div className="news-item" key={index} style={{ borderLeft: ".5px solid #d80000" }}>
                      <span className="bumb bumbSpecial">&#8226;</span>
                      {selectedSource === "all" && (
                        <strong className="news-source">{item.source}</strong>
                      )}
                      <span className="bumb" style={{ verticalAlign: "middle" }}>&#8226;</span>
                      <p
                        className="ago"
                        style={{
                          paddingLeft: selectedSource !== "all" ? "20px" : "0",
                        }}
                      >
                        {(() => {
                          const now = new Date();
                          const date = new Date(item.date);
                          const diffMs = now - date;
                          const diffMinutes = Math.floor(diffMs / 60000);
                          if (diffMinutes === 0) {
                            return `Chiar acum`;
                          } else if (diffMinutes === 1) {
                            return `Acum 1 minut`;
                          } else if (diffMinutes < 60) {
                            return diffMinutes > 19
                              ? `Acum ${diffMinutes} de minute`
                              : `Acum ${diffMinutes} minute`;
                          } else {
                            const hours = Math.floor(diffMinutes / 60);
                            const minutes = diffMinutes % 60;
                            const hourText =
                              hours === 1
                                ? "o oră"
                                : hours === 2
                                ? "două ore"
                                : `${hours} ore`;
                            const minuteText =
                              minutes === 0
                                ? ""
                                : minutes > 19
                                ? `${minutes} de minute`
                                : `${minutes} minute`;
                            return `Acum ${hourText}${minuteText ? ` și ${minuteText}` : ""}`;
                          }
                        })()}
                      </p>
                      {item.href && (
                        <a href={item.href} target="_blank" rel="noopener noreferrer">
                          <h3>{item.text}</h3>
                        </a>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          )}
          
          {/* Afișăm articolele cu imagine care NU fac parte din Carousel */}
          {sortedImageNews.length > 4 ? (
            <>
              {sortedImageNews.slice(4, visibleImageNewsCount).map((item, index) => (
                <div className="container-news" key={index}>
                  <img
                    src={item.imgSrc}
                    alt={item.text || "Image"}
                    className="news-image"
                  />
                  {item.href && (
                    <a href={item.href} target="_blank" rel="noopener noreferrer">
                      <div className="supra" style={{ border:".5px solid black" }}>
                        {item.source} <span className="bumb">&#8226;</span>
                        {(() => {
                          const now = new Date();
                          const date = new Date(item.date);
                          const diffMs = now - date;
                          const diffMinutes = Math.floor(diffMs / 60000);
                          if (diffMinutes === 0) {
                            return `Chiar acum`;
                          } else if (diffMinutes === 1) {
                            return `Acum 1 minut`;
                          } else if (diffMinutes < 60) {
                            return diffMinutes > 19
                              ? `Acum ${diffMinutes} de minute`
                              : `Acum ${diffMinutes} minute`;
                          } else {
                            const hours = Math.floor(diffMinutes / 60);
                            const minutes = diffMinutes % 60;
                            const hourText =
                              hours === 1
                                ? "o oră"
                                : hours === 2
                                ? "două ore"
                                : `${hours} ore`;
                            const minuteText =
                              minutes === 0
                                ? ""
                                : minutes > 19
                                ? `${minutes} de minute`
                                : `${minutes} minute`;
                            return `Acum ${hourText}${minuteText ? ` și ${minuteText}` : ""}`;
                          }
                        })()}
                      </div>
                      <h3>{item.text}</h3>
                      <p className="ago">
                        {selectedSource === "all" && (
                          <strong className="news-source">{item.source}</strong>
                        )}
                        <span className="bumb">&#8226;</span>
                        {(() => {
                          const now = new Date();
                          const date = new Date(item.date);
                          const diffMs = now - date;
                          const diffMinutes = Math.floor(diffMs / 60000);
                          if (diffMinutes === 0) {
                            return `Chiar acum`;
                          } else if (diffMinutes === 1) {
                            return `Acum 1 minut`;
                          } else if (diffMinutes < 60) {
                            return diffMinutes > 19
                              ? `Acum ${diffMinutes} de minute`
                              : `Acum ${diffMinutes} minute`;
                          } else {
                            const hours = Math.floor(diffMinutes / 60);
                            const minutes = diffMinutes % 60;
                            const hourText =
                              hours === 1
                                ? "o oră"
                                : hours === 2
                                ? "două ore"
                                : `${hours} ore`;
                            const minuteText =
                              minutes === 0
                                ? ""
                                : minutes > 19
                                ? `${minutes} de minute`
                                : `${minutes} minute`;
                            return `Acum ${hourText}${minuteText ? ` și ${minuteText}` : ""}`;
                          }
                        })()}
                      </p>
                    </a>
                  )}
                </div>
              ))}
              {/* Dacă mai există articole de afișat, se arată butonul de "Vezi mai multe știri" */}
              {sortedImageNews.length > visibleImageNewsCount && (
                <button onClick={handleLoadMore} className="load-more-button">
                  Vezi mai multe știri
                </button>
              )}
            </>
          ) : (
            // Dacă sunt 4 sau mai puține articole cu imagine, le afișăm pe toate fără Carousel
            sortedImageNews.map((item, index) => (
              <div className="container-news" key={index}>
                <img
                  src={item.imgSrc}
                  alt={item.text || "Image"}
                  className="news-image"
                />
                {item.href && (
                  <a href={item.href} target="_blank" rel="noopener noreferrer">
                    <h3>{item.text}</h3>
                    <p className="ago">
                      {selectedSource === "all" && (
                        <strong className="news-source">{item.source}</strong>
                      )}
                      <span className="bumb">&#8226;</span>
                      {(() => {
                        const now = new Date();
                        const date = new Date(item.date);
                        const diffMs = now - date;
                        const diffMinutes = Math.floor(diffMs / 60000);
                        if (diffMinutes === 0) {
                          return `Chiar acum`;
                        } else if (diffMinutes === 1) {
                          return `Acum 1 minut`;
                        } else if (diffMinutes < 60) {
                          return diffMinutes > 19
                            ? `Acum ${diffMinutes} de minute`
                            : `Acum ${diffMinutes} minute`;
                        } else {
                          const hours = Math.floor(diffMinutes / 60);
                          const minutes = diffMinutes % 60;
                          const hourText =
                            hours === 1
                              ? "o oră"
                              : hours === 2
                              ? "două ore"
                              : `${hours} ore`;
                          const minuteText =
                            minutes === 0
                              ? ""
                              : minutes > 19
                              ? `${minutes} de minute`
                              : `${minutes} minute`;
                          return `Acum ${hourText}${minuteText ? ` și ${minuteText}` : ""}`;
                        }
                      })()}
                    </p>
                  </a>
                )}
              </div>
            ))
          )}
        </div>
      )}
      
      {showScrollTop && (
        <div onClick={handleScrollTop} className="scroll-top" title="Scroll to top">
          ▲
        </div>
      )}
      
      {!loading && <Footer />}
    </div>
  );
};

export default App;
