import puppeteer from "puppeteer";
import mysql from "mysql2/promise";

const pool = mysql.createPool({
  host: process.env.MYSQL_ADDON_HOST,
  user: process.env.MYSQL_ADDON_USER,
  password: process.env.MYSQL_ADDON_PASSWORD,
  database: process.env.MYSQL_ADDON_DB,
  port: process.env.MYSQL_ADDON_PORT,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

const sitesConfig = {
  g4media: {
    url: "https://g4media.ro",
    tags: [{ tag: "div.post-review", contentSelector: "h3" }],
    cat: "Actualitate",
  },
  hotnews: {
    url: "https://hotnews.ro",
    tags: [{ tag: "article", contentSelector: "h2" }],
    cat: "Actualitate",
  },
  spotmedia: {
    url: "https://spotmedia.ro",
    tags: [{ tag: "div.jet-smart-listing__post", contentSelector: "div.mbm-h5" }],
    tags: [{ tag: "div.jet-smart-listing__post", contentSelector: "div.mbm-h6" }],
    cat: "Actualitate",
  },
  ziare: {
    url: "https://ziare.com",
    tags: [
      { tag: "div.spotlight__article", contentSelector: "h1.spotlight__article__title" },
      { tag: "div.spotlight__article", contentSelector: "h2.spotlight__article__title" },
      { tag: "div.news__article", contentSelector: "h3.news__article__title" },
    ],
    cat: "Actualitate",
  },
  digi24: {
    url: "https://digi24.ro",
    tags: [
      { tag: "article.article-alt", contentSelector: "h3.article-title" },
      { tag: "article", contentSelector: "h4.article-title" },      
    ],
    cat: "Actualitate",
  },
  libertatea: {
    url: "https://libertatea.ro",
    tags: [
      { tag: "div.news-item", contentSelector: "h3.article-title" },
      { tag: "div.news-item", contentSelector: "h2.article-title" },
    ],
    cat: "Actualitate",
  },
  stirileprotv: {
    url: "https://stirileprotv.ro",
    tags: [{ tag: "article.article", contentSelector: "h3.article-title-daily" }],
    cat: "Actualitate",
  }, 
  news: {
    url: "https://news.ro",
    tags: [{ tag: "article.article", contentSelector: "h2" }],
    cat: "Actualitate",
  }, 
  evz: {
    url: "https://evz.ro",
    tags: [{ tag: "div.banner-post-two", contentSelector: "h2.post-title" }],
    cat: "Actualitate",
  },
  gsp: {
    url: "https://gsp.ro",
    tags: [{ tag: "div.news-item", contentSelector: "h2" }],
    cat: "Sport",
  },          
  prosport: {
    url: "https://prosport.ro",
    tags: [{ tag: "div.article--wide", contentSelector: "h2.article__title" }],
    cat: "Sport",
  },   
  fanatik: {
    url: "https://fanatik.ro",
    tags: [{ tag: "div.article", contentSelector: "h3.article__title" }],
    cat: "Sport",
  },   
  csid: {
    url: "https://csid.ro",
    tags: [{ tag: "div.article", contentSelector: "h3.article__title" }],
    cat: "Sănătate",
  },
  viva: {
    url: "https://viva.ro",
    tags: [
      { tag: "article.art-small", contentSelector: "h3.art-title" },
      { tag: "article.art", contentSelector: "h3.art-title" },      
    ],
    cat: "Monden",
  }, 
  ciao: {
    url: "https://ciao.ro",
    tags: [
      { tag: "div.article", contentSelector: "h3.article__title" },
      { tag: "div.article", contentSelector: "h2.article__title" },      
    ],
    cat: "Monden",
  },                    
};

const gotoWithRetry = async (page, url, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
      return;
    } catch (error) {
      if (i === retries - 1) throw error;
      console.warn(`Retrying ${url}, attempt ${i + 1}`);
    }
  }
};

const scrapeTags = async (page, tags, source) => {
  const results = [];
  const seenLinks = new Set();

  for (const { tag, contentSelector } of tags) {
    const elements = await page.$$eval(
      tag,
      (elements, contentSelector, source) =>
        elements.map((el) => {
          const categoryElement = el.querySelector(".article__category");
          const category = categoryElement ? categoryElement.textContent.trim() : null;

          if (source === "fanatik" && category !== "Sport") {
            return null;
          }

          let imgSrc = null;
          const pictureElement = el.querySelector("picture");
          if (pictureElement) {
            const sourceElement = pictureElement.querySelector("source");
            if (sourceElement) {
              imgSrc = sourceElement.getAttribute("srcset");
            }

            const imgElement = pictureElement.querySelector("img");
            if (!imgSrc && imgElement) {
              imgSrc = imgElement.getAttribute("src");
            }
          }

          if (!imgSrc) {
            const imgElement = el.querySelector("img");
            imgSrc = imgElement?.getAttribute("src") || null;
          }

          if (imgSrc?.startsWith("data:image")) {
            imgSrc = null;
          }

          const contentElement = el.querySelector(contentSelector);
          const link = contentElement ? contentElement.querySelector("a") : null;

          return {
            imgSrc: imgSrc,
            text: contentElement ? contentElement.textContent.trim() : null,
            href: link ? link.href : null,
            category: category,
          };
        }),
      contentSelector,
      source
    );

    elements
      .filter((element) => element !== null)
      .forEach((element) => {
        if (element.href && !seenLinks.has(element.href)) {
          seenLinks.add(element.href);
          results.push({ ...element, source });
        }
      });
  }

  return results;
};

const processScrapedData = async (scrapedData, connection, source, cat) => {
  const insertQuery = `
    INSERT INTO articles (source, text, href, imgSrc, cat) 
    VALUES (?, ?, ?, ?, ?)
  `;

  for (const item of scrapedData) {
    const [existing] = await connection.query(
      "SELECT id FROM articles WHERE href = ?",
      [item.href]
    );

    if (existing.length === 0) {
      await connection.query(insertQuery, [
        item.source,
        item.text,
        item.href,
        item.imgSrc || null,
        cat,
      ]);
    }
  }
};

export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ message: "Method not allowed" });
  }

  const report = { totalScraped: 0, inserted: 0, skipped: 0, deleted: 0, details: [] };

  try {
    const browser = await puppeteer.launch({ headless: true });

    const connection = await pool.getConnection();
    try {
      const [deleteResult] = await connection.query(
        "DELETE FROM articles WHERE date < NOW() - INTERVAL 1 DAY"
      );
      report.deleted = deleteResult.affectedRows;

      for (const source in sitesConfig) {
        const { url, tags, cat } = sitesConfig[source];

        try {
          const page = await browser.newPage();
          await gotoWithRetry(page, url);

          const scrapedData = await scrapeTags(page, tags, source);
          report.totalScraped += scrapedData.length;

          await processScrapedData(scrapedData, connection, source, cat);

          await page.close();
        } catch (siteError) {
          console.error(`Error scraping site ${source}:`, siteError.message);
        }
      }
    } finally {
      connection.release();
    }

    await browser.close();

    console.log("\nScraping Report:");
    console.log(`- Total articles scraped: ${report.totalScraped}`);
    console.log(`- Total articles inserted: ${report.inserted}`);
    console.log(`- Total articles skipped: ${report.skipped}`);
    console.log(`- Total articles deleted: ${report.deleted}`);

    res.json({
      message: "Scraping completed.",
      report,
    });
  } catch (error) {
    console.error("Error in scraping:", error.message);
    res.status(500).json({ error: "Scraping failed" });
  }
}
