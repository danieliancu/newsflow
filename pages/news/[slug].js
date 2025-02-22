// pages/news/[slug].js
import React, { useState, useEffect } from "react";
import mysql from "mysql2/promise";
import dotenv from "dotenv";
import Head from "next/head";
import TimeAgo from "../../components/TimeAgo";
import { useRouter } from "next/router";
import Menu, { CategoryProvider } from "../../components/Menu";
import Footer from "@/components/Footer";
import ReactDOMServer from "react-dom/server"; // importăm pentru a obține markup-ul static
import { FaArrowLeft, FaExternalLinkAlt } from "react-icons/fa"; // iconiță pentru back

dotenv.config();

// Configurarea pool-ului pentru MySQL
const pool = mysql.createPool({
  host: process.env.MYSQL_ADDON_HOST,
  user: process.env.MYSQL_ADDON_USER,
  password: process.env.MYSQL_ADDON_PASSWORD,
  database: process.env.MYSQL_ADDON_DB,
  port: process.env.MYSQL_ADDON_PORT,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
  acquireTimeout: 30000,
});

const NewsDetail = ({ article }) => {
  const router = useRouter();
  const searchQuery = router.query.search;

  // State-uri pentru funcționalitatea de căutare din Top
  const [searchTerm, setSearchTerm] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [submittedSearchTerm, setSubmittedSearchTerm] = useState("");

  const handleCategoryFilter = (category) => {
    router.push(`/?category=${encodeURIComponent(category)}`);
  };

  // Funcții dummy pentru props
  const handleFilter = () => {};


  // Funcție care elimină SVG-urile și orice buton existent cu clasa "back-button-mobile" din .top-right-mobile,
// apoi inserează un singur buton cu iconul de back și textul "Înapoi"
const updateTopRightMobile = () => {
  const elements = document.querySelectorAll(".top-right-mobile");
  elements.forEach((el) => {
    // Elimină orice buton existent cu clasa "back-button-mobile"
    el.querySelectorAll("button.back-button-mobile").forEach((btn) => btn.remove());

    // Elimină toate elementele SVG din interiorul elementului
    el.querySelectorAll("svg").forEach((svg) => svg.remove());

    // Creează butonul de back
    const backButton = document.createElement("button");
    backButton.className = "back-button-mobile";
    
    // Obține markup-ul static al iconiței
    const iconMarkup = ReactDOMServer.renderToStaticMarkup(<FaArrowLeft />);
    backButton.innerHTML = iconMarkup + " Înapoi";

    // Setează evenimentul click pentru a naviga înapoi
    backButton.addEventListener("click", () => {
      window.history.back();
    });

    // Inserează butonul în elementul .top-right-mobile
    el.appendChild(backButton);
  });
};


  // Apelăm funcția updateTopRightMobile după montarea componentei
  useEffect(() => {
    updateTopRightMobile();
  }, []);

  return (
    <CategoryProvider>
      {/* Componenta Top cu funcționalitatea de căutare */}

      {/* Meniul cu categorii */}
      <Menu
        selectedCategory={article.cat}
        selectedSource={article.source}
        handleFilter={handleFilter}
        handleCategoryFilter={handleCategoryFilter}
        setSearchTerm={setSearchTerm}
        setIsSearching={setIsSearching}
        setSubmittedSearchTerm={setSubmittedSearchTerm}
      />

      <div className="news-detail-container">
        <Head>
          <title>{article.text}</title>
        </Head>
        <p className="label">{article.label}</p>
        <h1>{article.text}</h1>
        {article.imgSrc && (
          <div className="news-detail-image">
            <img src={article.imgSrc} alt={article.text} />
          </div>
        )}
        {article.intro && <p className="news-intro">{article.intro}</p>}
        <br /><br />
        <p style={{ border:"1px solid black", display:"inline-block", padding:"10px 15px", borderRadius:"10px", marginTop:"10px" }}>
          <TimeAgo date={article.date} source={article.source} />
          <a href={article.href}>{article.source} <FaExternalLinkAlt style={{ display:"inline-block", verticalAlign:"text-top" }} /></a>
          
        </p>
      </div>
      <Footer />
    </CategoryProvider>
  );
};

export async function getServerSideProps({ params }) {
  const { slug } = params;
  const parts = slug.split("-");
  const id = parts[parts.length - 1];

  try {
    const [rows] = await pool.query("SELECT * FROM articles WHERE id = ?", [id]);
    if (!rows || rows.length === 0) {
      return { notFound: true };
    }
    const article = rows[0];
    if (article.date) {
      article.date = article.date.toISOString();
    }
    return { props: { article } };
  } catch (error) {
    console.error("Error fetching article:", error);
    return { notFound: true };
  }
}

export default NewsDetail;
