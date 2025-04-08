import React, { useState, useEffect, useMemo, useReducer, useRef, useCallback } from "react";
import { Analytics } from "@vercel/analytics/react";
import { useRouter } from "next/router";

import Carousel from "./Carousel";
import Menu from "./Menu";
import Top from "./Top";
import Footer from "./Footer";
import SearchResults from "./SearchResults";
import ScrollToTop from "./ScrollToTop";
import Submenu from "./Submenu";
import { useFilteredArticles } from "./hooks/useFilteredArticles";
import NewsCard from "./NewsCard";

// Reducer pentru paginare pe categorii
const initialPaginationState = {};
function paginationReducer(state, action) {
  switch (action.type) {
    case "SET_PAGE":
      return {
        ...state,
        [action.category]: action.page,
      };
    case "RESET":
      return initialPaginationState;
    default:
      return state;
  }
}

// Reducer pentru memorarea poziției de scroll
const initialScrollState = {};
function scrollReducer(state, action) {
  switch (action.type) {
    case "SET_SCROLL":
      return {
        ...state,
        [action.category]: action.scrollPosition,
      };
    case "RESET":
      return initialScrollState;
    default:
      return state;
  }
}

const App = () => {
  const router = useRouter();

  useEffect(() => {
    if (router.isReady && router.query.category) {
      setSelectedCategory(router.query.category);
    }
  }, [router.isReady, router.query.category]);

  // Reduceri pentru paginare și scroll
  const [paginationState, dispatchPagination] = useReducer(
    paginationReducer,
    initialPaginationState
  );
  const [scrollState, dispatchScroll] = useReducer(
    scrollReducer,
    initialScrollState
  );

  // Referință pentru scroll
  const scrollRef = useRef();

  // Stări principale
  const [allData, setAllData] = useState([]);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [submittedSearchTerm, setSubmittedSearchTerm] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [selectedSource, setSelectedSource] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("Actualitate");
  const [loading, setLoading] = useState(true);
  const [selectedSort, setSelectedSort] = useState("Cele mai noi");

  // Stări pentru filtre suplimentare (Submenu)
  const [submenuSourceFilters, setSubmenuSourceFilters] = useState([]);
  const [submenuLabelFilters, setSubmenuLabelFilters] = useState([]);
  const [filtersByCategory, setFiltersByCategory] = useState({});
  const [isSubmenuPanelOpen, setIsSubmenuPanelOpen] = useState(false);

  // Definește numărul de articole afișate:
  const initialItems = 8;         // articolele afișate inițial
  const additionalItems = 50;       // articole adăugate la fiecare "Load more"

  // Stare pentru pagină curentă (folosită împreună cu reducerul)
  const [currentPage, setCurrentPage] = useState(
    paginationState[selectedCategory] || 1
  );

  // Fetch date la încărcare
  useEffect(() => {
    const fetchInitialData = async () => {
      setLoading(true);
      try {
        const response = await fetch("/api/articles?mode=initial");
        const result = await response.json();
        if (response.ok) {
          setAllData(result.data);
          // După afișarea inițială, se efectuează încărcarea completă în background
          fetchFullData();
        } else {
          setError(result.error || "Failed to fetch data");
        }
      } catch (error) {
        setError("Request failed");
      } finally {
        setLoading(false);
      }
    };

    const fetchFullData = async () => {
      try {
        const response = await fetch("/api/articles");
        const result = await response.json();
        if (response.ok) {
          // Actualizăm state-ul cu toate datele, fără a afecta vizualizarea curentă
          setAllData(result.data);
        }
      } catch (error) {
        console.error("Background fetch error:", error);
      }
    };

    fetchInitialData();
  }, []);

  // Actualizează filtrele locale când se schimbă categoria
  useEffect(() => {
    if (filtersByCategory[selectedCategory]) {
      setSubmenuSourceFilters(filtersByCategory[selectedCategory].sourceFilters);
      setSubmenuLabelFilters(filtersByCategory[selectedCategory].labelFilters);
    } else {
      setSubmenuSourceFilters([]);
      setSubmenuLabelFilters([]);
    }
  }, [selectedCategory, filtersByCategory]);

  // Salvăm poziția de scroll înainte de schimbarea categoriei
  useEffect(() => {
    const saveScrollPosition = () => {
      if (selectedCategory) {
        dispatchScroll({
          type: "SET_SCROLL",
          category: selectedCategory,
          scrollPosition: window.scrollY,
        });
      }
    };

    window.addEventListener("beforeunload", saveScrollPosition);
    return () => {
      window.removeEventListener("beforeunload", saveScrollPosition);
    };
  }, [selectedCategory]);

  // Aplicăm poziția de scroll memorată la revenirea pe categorie
  useEffect(() => {
    if (scrollState[selectedCategory] !== undefined) {
      window.scrollTo({
        top: scrollState[selectedCategory],
        behavior: "smooth",
      });
    }
  }, [selectedCategory, scrollState]);

  // Folosim noul hook pentru filtrare și sortare
  const { sortedImageNews, textNews } = useFilteredArticles(
    allData,
    selectedCategory,
    selectedSource,
    submenuSourceFilters,
    submenuLabelFilters,
    selectedSort
  );

  // Calculăm știrile totale (imagini + text)
  const totalFilteredNews = useMemo(
    () => sortedImageNews.concat(textNews),
    [sortedImageNews, textNews]
  );

  // Aplicăm regula pentru carousel (minim 5 știri)
  const carouselNews = useMemo(
    () => (totalFilteredNews.length >= 5 ? totalFilteredNews.slice(0, 4) : []),
    [totalFilteredNews]
  );

  // Știrile rămase după carousel
  const remainingNews = useMemo(
    () => totalFilteredNews.slice(carouselNews.length),
    [totalFilteredNews, carouselNews]
  );

  // Calculul articolelor vizibile: 
  // Dacă suntem la pagina 1 → afișăm initialItems; la fiecare pagină ulterioară adăugăm additionalItems
  const visibleNews = useMemo(() => {
    const currentPageNumber = paginationState[selectedCategory] || 1;
    const count =
      currentPageNumber === 1
        ? initialItems
        : initialItems + (currentPageNumber - 1) * additionalItems;
    return remainingNews.slice(0, count);
  }, [remainingNews, paginationState, selectedCategory]);

  // Funcția handleLoadMore: crește numărul de articole afișate cu 50 la fiecare click
  const handleLoadMore = useCallback(() => {
    const nextPage = (paginationState[selectedCategory] || 1) + 1;
    setCurrentPage(nextPage);
    dispatchPagination({
      type: "SET_PAGE",
      category: selectedCategory,
      page: nextPage,
    });
  }, [paginationState, selectedCategory]);

  // Optimizare cu useCallback pentru funcțiile transmise în componente:
  const handleFilter = useCallback((source) => {
    setSelectedSource(source);
    setCurrentPage(1);
    dispatchPagination({
      type: "SET_PAGE",
      category: selectedCategory,
      page: 1,
    });
  }, [selectedCategory]);

  const handleCategoryFilter = useCallback((category) => {
    if (!category) return;

    dispatchScroll({
      type: "SET_SCROLL",
      category: selectedCategory,
      scrollPosition: window.scrollY,
    });

    setSubmittedSearchTerm("");
    setSelectedCategory(category);
    setCurrentPage(paginationState[category] || 1);
    setSelectedSource("all");

    if (scrollState[category] !== undefined) {
      window.scrollTo({
        top: scrollState[category],
        behavior: "smooth",
      });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [paginationState, scrollState, selectedCategory]);

  // updateSourceFilters, updateLabelFilters, resetFilters și alte callback-uri rămân neschimbate...
  const updateSourceFilters = useCallback((newSourceFilters) => {
    setSubmenuSourceFilters(newSourceFilters);
    setFiltersByCategory((prev) => ({
      ...prev,
      [selectedCategory]: {
        sourceFilters: newSourceFilters,
        labelFilters: submenuLabelFilters,
      },
    }));
  }, [submenuLabelFilters, selectedCategory]);

  const updateLabelFilters = useCallback((newLabelFilters) => {
    setSubmenuLabelFilters(newLabelFilters);
    setFiltersByCategory((prev) => ({
      ...prev,
      [selectedCategory]: {
        sourceFilters: submenuSourceFilters,
        labelFilters: newLabelFilters,
      },
    }));
  }, [submenuSourceFilters, selectedCategory]);

  const resetFilters = useCallback(() => {
    setSubmenuSourceFilters([]);
    setSubmenuLabelFilters([]);
    setFiltersByCategory((prev) => ({
      ...prev,
      [selectedCategory]: { sourceFilters: [], labelFilters: [] },
    }));
  }, [selectedCategory]);

  // ursele și etichetele disponibile pentru categoria selectată
  const availableSourcesForCategory = useMemo(() => 
    Array.from(
      new Set(
        allData.filter((item) => item.cat === selectedCategory)
               .map((item) => item.source)
      )
    ),
    [allData, selectedCategory]
  );

  const availableLabelsForCategory = useMemo(() => 
    Array.from(
      new Set(
        allData.filter((item) => item.cat === selectedCategory)
               .map((item) => item.label)
      )
    ),
    [allData, selectedCategory]
  );

  // Calculăm totalul știrilor pentru butonul "Încarcă mai multe"
  const totalNewsCount = useMemo(() => remainingNews.length, [remainingNews]);

  // Randare UI
  return (
    <div ref={scrollRef}>
      {/* 🔝 Bara de căutare */}
      <Top
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        setIsSearching={setIsSearching}
        submittedSearchTerm={submittedSearchTerm}
        setSubmittedSearchTerm={setSubmittedSearchTerm}
      />

      {/* Meniu Categorii și Surse */}
      <Menu
        selectedSource={selectedSource}
        selectedCategory={selectedCategory}
        handleFilter={handleFilter}
        handleCategoryFilter={handleCategoryFilter}
        availableSources={availableSourcesForCategory}
        availableCategories={Array.from(new Set(allData.map((item) => item.cat)))}
        setSearchTerm={setSearchTerm}
        setIsSearching={setIsSearching}
        setSubmittedSearchTerm={setSubmittedSearchTerm}
      />

      {/* Submeniu pentru filtre suplimentare */}
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

      {/* Indicator de încărcare sau afișarea știrilor */}
      {loading ? (
        <div>
          <div className="loading">
            <div className="spinner"></div>
          </div>
          <p style={{
            textAlign: "center",
            color: "var(--red)",
            padding: "20px",
            fontWeight: "bold",
          }}>
            Se încarcă ultimele știri
          </p>
        </div>
      ) : submittedSearchTerm.trim() ? (
        // Rezultate căutare
        <SearchResults searchTerm={submittedSearchTerm} allData={allData} />
      ) : (
        // Știri filtrate cu paginare și memorie
        <div className="container grid-layout">
          {/* Carusel */}
          {carouselNews.length >= 4 && (
            <Carousel key={selectedSource} items={carouselNews} />
          )}

          {/* Mesaje pentru rezultatele filtrate */}
          {totalFilteredNews.length === 0 ? (
            <p style={{ textAlign: "center", fontWeight: "bold", padding: "20px" }}>
              Nu s-a găsit nicio știre pentru acest filtru
            </p>
          ) : visibleNews.length > 0 ? (
            visibleNews.map((item) => (
              <NewsCard key={item.id} item={item} selectedSource={selectedSource} />
            ))
          ) : (
            <p style={{ textAlign: "center", fontWeight: "bold", padding: "20px" }}>
              Încarcă mai multe pentru a vedea rezultatele
            </p>
          )}

          {/* Butonul "Încarcă mai multe" */}
          {visibleNews.length < totalNewsCount && (
            <div style={{ textAlign: "center", paddingTop: "40px", width: "100%" }}>
              <button
                onClick={handleLoadMore}
                style={{
                  padding: "10px 20px",
                  fontSize: "16px",
                  fontWeight: "bold",
                  backgroundColor: "var(--black)",
                  color: "white",
                  border: "none",
                  cursor: "pointer",
                  borderRadius: "5px",
                }}
              >
                Mai multe știri
              </button>
            </div>
          )}
        </div>
      )}

      {/* Buton Scroll Top */}
      <ScrollToTop />

      {/* Footer */}
      {!loading && <Footer />}

      {/* Analytics */}
      <Analytics />
    </div>
  );
};

export default App;
