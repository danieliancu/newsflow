import React, { useState, useEffect } from "react";
import mysql from "mysql2/promise";
import dotenv from "dotenv";
import Head from "next/head";
import TimeAgo from "../../components/TimeAgo";
import { useRouter } from "next/router";
import Menu, { CategoryProvider } from "../../components/Menu";
import Footer from "@/components/Footer";
import ReactDOMServer from "react-dom/server"; 
import { FaArrowLeft, FaExternalLinkAlt } from "react-icons/fa"; 
// Am înlocuit importul din react-share cu cel din next-share
import { FacebookIcon, FacebookShareButton, TwitterIcon, TwitterShareButton } from "next-share";
import Link from "next/link";

dotenv.config();

// Configurarea conexiunii la MySQL
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

const NewsDetail = ({ article, slug }) => {
  const router = useRouter();

  // State-uri pentru funcționalitatea de căutare din Top
  const [searchTerm, setSearchTerm] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [submittedSearchTerm, setSubmittedSearchTerm] = useState("");

  const handleCategoryFilter = (category) => {
    router.push(`/?category=${encodeURIComponent(category)}`);
  };

  // Eliminarea butoanelor SVG și adăugarea butonului "Înapoi"
  const updateTopRightMobile = () => {
    const elements = document.querySelectorAll(".top-right-mobile");
    elements.forEach((el) => {
      el.querySelectorAll("button.back-button-mobile").forEach((btn) => btn.remove());
      el.querySelectorAll("svg").forEach((svg) => svg.remove());

      const backButton = document.createElement("button");
      backButton.className = "back-button-mobile";
      backButton.innerHTML = ReactDOMServer.renderToStaticMarkup(<FaArrowLeft />) + " Înapoi";
      backButton.addEventListener("click", () => {
        window.history.back();
      });

      el.appendChild(backButton);
    });
  };

  useEffect(() => {
    updateTopRightMobile();
  }, []);

  return (
    <CategoryProvider>
      <Menu
        selectedCategory={article.cat}
        selectedSource={article.source}
        handleFilter={() => {}}
        handleCategoryFilter={handleCategoryFilter}
        setSearchTerm={setSearchTerm}
        setIsSearching={setIsSearching}
        setSubmittedSearchTerm={setSubmittedSearchTerm}
      />

      <div className="news-detail-container">
        {/* 🔹 SEO: Meta Tag-uri personalizate */}
        <Head>
          <title>{article.text} | Newsflow</title>
          <meta name="description" content={article.intro || article.text} />
          <meta property="og:title" content={article.text} />
          <meta property="og:description" content={article.intro || article.text} />
          <meta property="og:image" content={`https://newsflow.ro${article.imgSrc || "/images/default.png"}`} />
          <meta property="og:type" content="article" />
          <meta property="og:url" content={`https://newsflow.ro/news/${slug}`} />
          <meta property="og:site_name" content="Newsflow - Cele mai recente știri" />
          <meta property="fb:app_id" content="1309016446837808" />
          <meta name="twitter:card" content="summary_large_image" />
          <meta name="twitter:title" content={article.text} />
          <meta name="twitter:description" content={article.intro || article.text} />
          <meta name="twitter:image" content={`https://newsflow.ro${article.imgSrc || "/images/default.png"}`} />
          <link rel="canonical" href={`https://newsflow.ro/news/${slug}`} />

          <script type="application/ld+json" dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "NewsArticle",
              "headline": article.text,
              "image": article.imgSrc || "/images/default.png",
              "datePublished": article.date,
              "dateModified": article.date,
              "author": {
                "@type": "Organization",
                "name": "Newsflow"
              },
              "publisher": {
                "@type": "Organization",
                "name": "Newsflow",
                "logo": {
                  "@type": "ImageObject",
                  "url": "https://newsflow.ro/logo.png"
                }
              },
              "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": `https://newsflow.ro/news/${slug}`
              }
            })
          }} />
        </Head>
        <nav className="breadcrumbs">
          <Link href="/">Acasă</Link> &gt;
          <span>{article.cat}</span> &gt;
          <span>{article.text}</span>
        </nav>    
        <p className="label">{article.label}</p>
        <h1>{article.text}</h1>

        {article.imgSrc && (
          <div className="news-detail-image">
            <img src={article.imgSrc} alt={article.text} />
          </div>
        )}

        {article.intro && <p className="news-intro">{article.intro}</p>}
        <br /><br />
        <div style={{ display:"flex", justifyContent: "space-between", alignItems: "center" }}>
          <p style={{ border: "1px solid black", display: "inline-block", padding: "10px 15px", borderRadius: "10px", marginTop: "10px" }}>
            <TimeAgo date={article.date} source={article.source} />
            <a href={article.href} target="_blank" rel="noopener noreferrer">
              {article.source} <FaExternalLinkAlt style={{ display: "inline-block", verticalAlign: "text-top" }} />
            </a>
          </p>
          <div>
            {/* Utilizare next-share în locul react-share */}
            <FacebookShareButton url={`https://newsflow.ro/news/${slug}`} quote={article.text}>
              <FacebookIcon size={32} style={{ color: "var(--black)", padding:"5px" }} />
            </FacebookShareButton>

            <TwitterShareButton url={`https://newsflow.ro/news/${slug}`} title={article.text}>
              <TwitterIcon size={32} style={{ color: "var(--black)", padding:"5px" }} />
            </TwitterShareButton>
          </div>          
        </div>
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

    // Funcție care elimină diacriticele specifice limbii române
    const removeDiacritics = (str) => {
      // Mapare manuală pentru caracterele specifice limbii române
      const diacriticsMap = {
        "ă": "a",
        "â": "a",
        "î": "i",
        "ș": "s",
        "ş": "s",
        "ț": "t",
        "ţ": "t"
      };
      return str
        .split('')
        .map(char => diacriticsMap[char] || char)
        .join('');
    };

    // 🔹 Generăm slug-ul corect pentru SEO folosind removeDiacritics
    const generatedSlug = removeDiacritics(article.text)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

    return { props: { article, slug: `${generatedSlug}-${article.id}` } };
  } catch (error) {
    console.error("Error fetching article:", error);
    return { notFound: true };
  }
}


export default NewsDetail;
