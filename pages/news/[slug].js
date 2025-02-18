// pages/news/[slug].js
import React from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import NewsCard from "../../components/NewsCard"; // Ajustează calea după necesitate

export default function NewsPage({ newsItem, otherNews }) {
  const router = useRouter();

  if (router.isFallback) {
    return <div>Se încarcă...</div>;
  }

  if (!newsItem) {
    return <div>Știre negăsită.</div>;
  }

  return (
    <div style={{ padding: "20px" }}>
      <Link href="/">&#8592; Înapoi la pagina principală</Link>
      <div>
        <h1>{newsItem.text}</h1>
        <p>
          <strong>Etichetă:</strong> {newsItem.label}
        </p>
        {newsItem.imgSrc && (
          <img
            src={newsItem.imgSrc}
            alt={newsItem.text}
            style={{ maxWidth: "100%", height: "auto" }}
          />
        )}
        <p>
          <strong>Sursa:</strong> {newsItem.source}
        </p>
        <p>
          <strong>Data:</strong>{" "}
          {new Date(newsItem.date).toLocaleString()}
        </p>
        <p>
          <strong>Introducere:</strong> {newsItem.intro}
        </p>
        <p>
          <strong>Link original:</strong>{" "}
          <a
            href={newsItem.href}
            target="_blank"
            rel="noopener noreferrer"
          >
            {newsItem.href}
          </a>
        </p>
      </div>
      <div style={{ marginTop: "40px" }}>
        <h2>Alte știri din {newsItem.cat}</h2>
        <div>
          {otherNews && otherNews.length > 0 ? (
            otherNews.map((item) => (
              <NewsCard key={item.id} item={item} selectedSource="all" />
            ))
          ) : (
            <p>Nu există alte știri în această categorie.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export async function getStaticPaths() {
  return {
    paths: [],
    fallback: true,
  };
}

export async function getStaticProps({ params }) {
  const { slug } = params;
  const parts = slug.split("-");
  const id = parts[parts.length - 1];
  const idNumber = Number(id);

  try {
    // Preluăm articolul principal
    const res = await fetch(`http://localhost:3000/api/articles?id=${id}`);
    if (!res.ok) {
      return { notFound: true };
    }
    const data = await res.json();
    let article;
    if (Array.isArray(data.data)) {
      article = data.data.find((item) => item.id === idNumber);
    } else {
      article = data.data;
    }
    if (!article) {
      return { notFound: true };
    }

    const minimalNewsItem = {
      id: article.id ?? null,
      text: article.text ?? null,
      label: article.label ?? null,
      imgSrc: article.imgSrc ?? null,
      source: article.source ?? null,
      date: article.date ?? null,
      href: article.href ?? null,
      intro: article.intro ?? null,
      cat: article.cat ?? null,
    };

    // Preluăm toate articolele și filtrăm pentru cele din aceeași categorie
    const resAll = await fetch(`http://localhost:3000/api/articles`);
    if (!resAll.ok) {
      return { notFound: true };
    }
    const dataAll = await resAll.json();
    const allArticles = Array.isArray(dataAll.data)
      ? dataAll.data
      : [dataAll.data];

    const otherNews = allArticles
      .filter(
        (item) =>
          item.cat === minimalNewsItem.cat &&
          item.id !== minimalNewsItem.id
      )
      .map((item) => ({
        id: item.id ?? null,
        text: item.text ?? null,
        label: item.label ?? null,
        imgSrc: item.imgSrc ?? null,
        source: item.source ?? null,
        date: item.date ?? null,
        href: item.href ?? null,
        intro: item.intro ?? null,
        cat: item.cat ?? null,
      }))
      .slice(0, 10); // Limităm la 10 articole

    return {
      props: { newsItem: minimalNewsItem, otherNews },
      revalidate: 60,
    };
  } catch (error) {
    return { notFound: true };
  }
}
