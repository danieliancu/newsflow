import React, { useState, useEffect } from "react";
import { FaBars, FaTimes } from "react-icons/fa";

const Menu = ({
  selectedSource,
  selectedCategory,
  handleFilter,
  handleCategoryFilter,
  availableSources,
}) => {
  const [menuOpen, setMenuOpen] = useState(false); // Starea pentru meniu
  const categories = ["Actualitate", "Economie", "Sport", "Sănătate", "Monden"];
  
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 766) {
        setMenuOpen(true);
      } else {
        setMenuOpen(false);
      }
    };

    // Setăm valoarea inițială
    handleResize();

    // Adăugăm și curățăm listener-ul
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggleMenu = () => {
    setMenuOpen((prev) => !prev);
  };

  const handleCategorySelect = (category) => {
    handleCategoryFilter(category);
    setMenuOpen(false); // Închide meniul după selectarea categoriei
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
          
          {/* Afișăm FaBars sau FaTimes în funcție de starea meniului */}
          {menuOpen ? (
            <FaTimes className="hamburger" onClick={toggleMenu} />
          ) : (
            <FaBars className="hamburger" onClick={toggleMenu} />
          )}
        </div>

        {/* Meniul de categorii */}
        <div
          className="menu-categories"
          style={{ display: menuOpen ? "block" : "none" }}
        >
          {categories.map((category) => (
            <div
              key={category}
              onClick={() => handleCategorySelect(category)} // Închide meniul la selectare
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

        {/* Secțiunea de surse (ascunsă deocamdată) */}
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
