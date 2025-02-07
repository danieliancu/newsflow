import React, { useState, useEffect } from "react";
import { FaBars, FaTimes, FaUser, FaSearch } from "react-icons/fa";

const Menu = ({
  selectedSource,
  selectedCategory,
  handleFilter,
  handleCategoryFilter,
  availableSources,
  availableCategories,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const categories = availableCategories || [];

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

  // Funcția care adaugă / elimină clasa pe body
  const toggleSearchOnMobile = () => {
    document.body.classList.toggle("search-open");
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
            {/* Aici se face togglingul pentru search */}
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

        <div
          className="menu-categories"
          style={{ display: menuOpen ? "block" : "none" }}
        >
          {categories.map((category) => (
            <div
              key={category}
              onClick={() => {
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
              className={`menu-item ${
                selectedCategory === category ? "active" : ""
              }`}
            >
              {category}
            </div>
          ))}
        </div>

        {/* Surse ascunse - doar ca exemplu */}
        <div style={{ display: "none" }}>
          <button
            style={{ color: "red", padding: "0 10px" }}
            onClick={() => handleFilter("all")}
            className={selectedSource === "all" ? "active" : ""}
          >
            Toate sursele
          </button>
          {availableSources.map((source) => (
            <button
              key={source}
              onClick={() => handleFilter(source)}
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
