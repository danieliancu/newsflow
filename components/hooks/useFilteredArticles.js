import { useMemo } from "react";

export const useFilteredArticles = (
    allData,
    selectedCategory,
    selectedSource,
    submenuSourceFilters,
    submenuLabelFilters,
    selectedSort
  ) => {
  // Filtrare inițială după sursă și categorie
  const filteredData = useMemo(() => {
    let data = [...allData];

    if (selectedSource !== "all") {
      data = data.filter((item) => item.source === selectedSource);
    }

    if (selectedCategory) {
      data = data.filter((item) => item.cat === selectedCategory);
    }

    return data;
  }, [allData, selectedSource, selectedCategory]);

  // Aplicăm filtre suplimentare din Submenu
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

  // Funcție de sortare
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

  // Separăm știrile cu imagini de cele fără imagini
  const sortedImageNews = useMemo(() => {
    return sortData(finalFilteredData.filter((item) => item.imgSrc));
  }, [finalFilteredData, selectedSort]);

  const textNews = useMemo(() => {
    return sortData(finalFilteredData.filter((item) => !item.imgSrc));
  }, [finalFilteredData, selectedSort]);

  return { sortedImageNews, textNews };
};

export default useFilteredArticles;
