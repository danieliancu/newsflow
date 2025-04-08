import React, { createContext, useContext, useState, useEffect } from "react";
import { FaBars, FaTimes, FaUser, FaSearch } from "react-icons/fa";
import Link from "next/link";

// Creăm contextul cu o valoare implicită (fallback)
const CategoryContext = createContext({
  availableCategories: [],
  availableSources: [],
});

// Providerul contextului, care setează valorile dinamice
export const CategoryProvider = ({ children }) => {
  const [availableCategories, setAvailableCategories] = useState([]);
  const [availableSources, setAvailableSources] = useState([]);

  useEffect(() => {
    // Valorile pot fi încărcate dinamic (fetch) – aici sunt valori statice de exemplu:
    setAvailableCategories([
      "Actualitate",
      "Agricultură",
      "Economie",
      "Mame și copii",
      "Monden",
      "Sănătate",
      "Sport",
    ]);
    setAvailableSources(["Source1", "Source2", "Source3"]);
  }, []);

  return (
    <CategoryContext.Provider
      value={{ availableCategories, availableSources }}
    >
      {children}
    </CategoryContext.Provider>
  );
};

// Hook-ul personalizat pentru a accesa contextul
export const useCategoryContext = () => useContext(CategoryContext);

// Componenta Menu care folosește contextul pentru a obține categoriile și sursele
const Menu = ({
  selectedSource,
  selectedCategory,
  handleFilter,
  handleCategoryFilter,
  setSearchTerm,
  setIsSearching,
  setSubmittedSearchTerm,
  availableCategories: propCategories,
  availableSources: propSources,
}) => {
  // Dacă nu primesc prin props, folosesc valorile din context
  const { availableCategories, availableSources } = useCategoryContext();
  const categories = (propCategories || availableCategories || [])
    .slice()
    .sort((a, b) => a.localeCompare(b));
  const sources = (propSources || availableSources || [])
    .slice()
    .sort((a, b) => a.localeCompare(b));

  const [isMobile, setIsMobile] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 767);
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggleSearchOnMobile = () => {
    document.body.classList.toggle("search-open");
    setIsSearchOpen((prev) => !prev);
  };

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
              newsflow<span style={{ color: "var(--red)" }}>.</span>ro
            </a>
          </h1>
          <span className="top-right-mobile">
            <FaUser className="login" style={{ fill: "white", fontSize: "24px" }} />
            {isSearchOpen ? (
              <FaTimes
                className="search-mobile"
                style={{ fill: "red", fontSize: "24px", paddingRight: "5px" }}
                onClick={toggleSearchOnMobile}
              />
            ) : (
              <FaSearch
                className="search-mobile"
                style={{ fill: "white", fontSize: "24px" }}
                onClick={toggleSearchOnMobile}
              />
            )}
          </span>
        </div>
        <div className="menu-categories-faded"></div>
        {/* Lista categoriilor */}
        <div className="menu-categories">
          {categories.map((category) => (
            <div
              key={category}
              onClick={() => {
                resetSearch();
                handleCategoryFilter(category);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              style={
                isMobile
                  ? { color: selectedCategory === category ? "var(--red)" : "white" }
                  : { borderBottom: selectedCategory === category ? "4px solid #d80000" : "none" }
              }
              className={`menu-item ${selectedCategory === category ? "active" : ""}`}
            >
              {category}
            </div>
          ))}
          {/* Buton de Arhivă */}
          <Link href="/archive">
            <div
              className={`menu-item ${selectedCategory === "archive" ? "active" : ""}`}
              style={isMobile ? { color: "white" } : { borderBottom: "none" }}
            >
              Arhivă
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Menu;
