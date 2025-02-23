import { SitemapStream, streamToPromise } from "sitemap";
import { createGzip } from "zlib";
import mysql from "mysql2/promise";

export default async function handler(req, res) {
  try {
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

    const [articles] = await pool.query("SELECT id, text FROM articles");

    // Crearea fluxului Sitemap
    const sitemap = new SitemapStream({ hostname: "https://newsflow.ro" });
    const pipeline = sitemap.pipe(createGzip());

    // Adaugă homepage-ul
    sitemap.write({ url: "/", changefreq: "daily", priority: 1.0 });

    // Adaugă fiecare știre în sitemap
    articles.forEach((article) => {
      const slug = article.text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      sitemap.write({
        url: `/news/${slug}-${article.id}`,
        changefreq: "daily",
        priority: 0.8,
      });
    });

    sitemap.end();

    // Returnează sitemap-ul comprimat
    const sitemapBuffer = await streamToPromise(pipeline);
    res.setHeader("Content-Type", "application/xml");
    res.setHeader("Content-Encoding", "gzip");
    res.send(sitemapBuffer);
  } catch (error) {
    console.error("Eroare generare sitemap:", error);
    res.status(500).send("Eroare generare sitemap");
  }
}
