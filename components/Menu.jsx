import React, { useState, useEffect } from "react";
import { FaBars, FaTimes, FaUser, FaSearch } from "react-icons/fa";

const Menu = ({
  selectedSource,
  selectedCategory,
  handleFilter,
  handleCategoryFilter,
  availableSources,
  availableCategories,
  // Props pentru resetare căutare:
  setSearchTerm,
  setIsSearching,
  setSubmittedSearchTerm
}) => {
  const [menuOpen, setMenuOpen] = useState(false);

  // Sortează dinamic categoriile
  const categories = (availableCategories || []).slice().sort((a, b) =>
    a.localeCompare(b)
  );

  // Sortează dinamic sursele
  const sources = (availableSources || []).slice().sort((a, b) =>
    a.localeCompare(b)
  );

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 766) {
        setMenuOpen(true);
      } else {
        setMenuOpen(false);
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggleMenu = () => {
    setMenuOpen((prev) => !prev);
  };

  // Toggle pentru search bar pe mobil (dacă ai un CSS dedicat .search-open)
  const toggleSearchOnMobile = () => {
    document.body.classList.toggle("search-open");
  };

  // Funcție care anulează căutarea și golește inputul
  const resetSearch = () => {
    setSearchTerm("");           
    setIsSearching(false);       
    setSubmittedSearchTerm("");  
  };

  return (
    <div className="menu">
      <div className="menu-container">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            width: "100%",
            justifyContent: "space-between",
            position: "relative",
          }}
        >
          <h1 className="logo">
            <img
              src="/images/giphy_transparent.gif"
              alt="Loading"
              className="giphy"
            />
            <a href="/">
              newsflow<span style={{ color: "#d80000" }}>.ro</span>
            </a>
          </h1>
          <span className="top-right-mobile">
            <FaUser className="login" style={{ fill: "white", fontSize: "24px" }} />
            <FaSearch
              className="search-mobile"
              style={{ fill: "white", fontSize: "24px" }}
              onClick={toggleSearchOnMobile}
            />
          </span>

          {menuOpen ? (
            <FaTimes className="hamburger" onClick={toggleMenu} />
          ) : (
            <FaBars className="hamburger" onClick={toggleMenu} />
          )}
        </div>

        {/* LISTA CATEGORII */}
        <div
          className="menu-categories"
          style={{ display: menuOpen ? "block" : "none" }}
        >
          {categories.map((category) => (
            <div
              key={category}
              onClick={() => {
                resetSearch();
                handleCategoryFilter(category);

                if (window.innerWidth < 600) {
                  setMenuOpen(false);
                }
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              style={{
                borderBottom:
                  selectedCategory === category ? "4px solid #d80000" : "none",
              }}
              className={`menu-item ${selectedCategory === category ? "active" : ""}`}
            >
              {category}
            </div>
          ))}
        </div>

        {/* LISTA SURSE (dacă vrei să o afișezi) */}
        <div style={{ display: "none" }}>
          <button
            style={{ color: "red", padding: "0 10px" }}
            onClick={() => {
              resetSearch();
              handleFilter("all");
            }}
            className={selectedSource === "all" ? "active" : ""}
          >
            Toate sursele
          </button>
          {sources.map((source) => (
            <button
              key={source}
              onClick={() => {
                resetSearch();
                handleFilter(source);
              }}
              className={selectedSource === source ? "active" : ""}
            >
              {source}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Menu;
