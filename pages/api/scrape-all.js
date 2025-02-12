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
    tags: [
      { tag: "div.jet-smart-listing__post", contentSelector: "div.mbm-h5" },
      { tag: "div.jet-smart-listing__post", contentSelector: "div.mbm-h6" }
    ],
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
  adevarul: {
    url: "https://adevarul.ro",
    tags: [{ tag: "div.container", contentSelector: "div.svelte-4dr2hm" }],
    cat: "Actualitate",
  },  
  observatornews: {
    url: "https://observatornews.ro",
    tags: [
      { tag: "div.item.breaking-news-last", contentSelector: "span.stire-h3" }, // Breaking news
      { tag: "div.stire", contentSelector: "h3" }, // Articole standard
      { tag: "div.stire-simpla", contentSelector: "span.stire-h3" } // Știri simple
    ],
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
  clicksanatate: {
    url: "https://clicksanatate.ro",
    tags: [
      { tag: "div.entry.co-3.svelte-1wok1io", contentSelector: "a.title.svelte-1wok1io" }
    ],
    cat: "Sănătate",
  },  
  totuldespremame: {
    url: "https://totuldespremame.ro",
    tags: [
      { tag: "div.post-vertical", contentSelector: "h3.post-title" },
      { tag: "div.post", contentSelector: "h2.post-title" }, 
      { tag: "div.post-horizontal", contentSelector: "h3.post-title" },    
      { tag: "div.post", contentSelector: "h3.post-title" },   
    ],
    cat: "Mame și copii",
  }, 
  superbebe: {
    url: "https://superbebe.ro",
    tags: [{ tag: "div.td_module_mx3", contentSelector: "h3.entry-title" }],
    cat: "Mame și copii",
  },   
  desprecopii: {
    url: "https://desprecopii.com/noutati",
    tags: [{ tag: ".blog-list div.item", contentSelector: "h3" }],
    cat: "Mame și copii",
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
  okmagazine: {
    url: "https://okmagazine.ro",
    tags: [
      { tag: "div.entry.co-3.svelte-1ds0vto", contentSelector: "a.title.svelte-1ds0vto" }
    ],
    cat: "Monden",
  },  
  agrobiznes: {
    url: "https://agrobiznes.ro",
    tags: [
      { tag: "div.td_module_flex", contentSelector: "h3.entry-title" }
    ],
    cat: "Agricultură",
  }, 
  agrointel: {
    url: "https://agrointel.ro",
    tags: [
      { tag: "a.excerpt", contentSelector: "b cite" }
    ],
    cat: "Agricultură",
  },      
};

const gotoWithRetry = async (page, url, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
      return;
    } catch (error) {
      if (i === retries - 1) throw error; // Re-aruncă eroarea dacă este ultima încercare
      console.warn(`Retrying ${url}, attempt ${i + 1}`);
    }
  }
};



const scrapeTags = async (page, tags, source) => {
  const seenLinks = new Set();

  // Calculăm prefixele acceptate pentru validarea href
  let allowedPrefixes = null;
  if (source !== "desprecopii") {
    if (source === "ziare") {
      allowedPrefixes = ["https://ziare.com/", "https://www.ziare.com/"];
    } else {
      // Extragem domeniul din url; dacă se dorește, se poate defini explicit și în sitesConfig
      const domain = sitesConfig[source]?.domain || new URL(sitesConfig[source].url).hostname;
      allowedPrefixes = [`https://${domain}/`, `https://www.${domain}/`];
    }
  }

  // Procesăm fiecare selector în paralel
  const scrapedArrays = await Promise.all(
    tags.map(async ({ tag, contentSelector }) => {
      return await page.$$eval(
        tag,
        (elements, contentSelector, source, allowedPrefixes) => {
          // Helper: extragerea imaginii
          const extractImgSrc = (el) => {
            let src = null;
            switch (source) {
              case "adevarul": {
                const img = el.querySelector("img");
                src = img ? img.getAttribute("src") : null;
                break;
              }
              case "observatornews": {
                const img = el.querySelector("figure img");
                src = img ? img.getAttribute("src") : null;
                break;
              }
              case "clicksanatate":
              case "okmagazine": {
                const img = el.querySelector("a.image picture img");
                src = img ? img.getAttribute("src") : null;
                break;
              }
              default: {
                const pictureEl = el.querySelector("picture");
                if (pictureEl) {
                  const sourceEl = pictureEl.querySelector("source");
                  if (sourceEl) {
                    src = sourceEl.getAttribute("srcset");
                  }
                  if (!src) {
                    const img = pictureEl.querySelector("img");
                    src = img ? img.getAttribute("src") : null;
                  }
                }
                if (!src) {
                  const img = el.querySelector("img");
                  src = img ? img.getAttribute("src") : null;
                }
              }
            }
            // Excludem imaginile inline/Base64
            return src && src.startsWith("data:image") ? null : src;
          };

          // Helper: extragerea link-ului și a titlului
          const extractLinkAndTitle = (el, contentSelector) => {
            let link = null;
            let title = null;
            const contentEl = el.querySelector(contentSelector);
            if (contentEl) {
              link = contentEl.querySelector("a");
              title = contentEl.textContent.trim();
            }

            // Tratare specifică pentru observatornews.ro
            if (source === "observatornews") {
              if (el.matches("div.item.breaking-news-last") || el.matches("div.stire")) {
                link = el.querySelector("a.full-link");
              } else if (el.matches("div.stire-simpla")) {
                const links = el.querySelectorAll("a");
                link = links[1] || link;
              }
            }

            // Pentru clicksanatate.ro și okmagazine.ro, titlul e în atributul "title"
            if (source === "clicksanatate" || source === "okmagazine") {
              link = el.querySelector("a.title");
              title = link ? link.getAttribute("title") : title;
            }
            return { link, title };
          };

          return elements.map((el) => {
            // Verificăm categoria pentru sursa "fanatik"
            const categoryEl = el.querySelector(".article__category");
            const category = categoryEl ? categoryEl.textContent.trim() : null;
            if (source === "fanatik" && category !== "Sport") return null;

            // Extragem imaginea, link-ul și titlul
            const imgSrc = extractImgSrc(el);
            const { link, title } = extractLinkAndTitle(el, contentSelector);
            const href = link ? link.href : null;

            // Validăm href dacă avem prefixe acceptate
            if (allowedPrefixes && (!href || !allowedPrefixes.some(prefix => href.startsWith(prefix)))) {
              return null;
            }

            return { imgSrc, text: title, href, category };
          });
        },
        contentSelector,
        source,
        allowedPrefixes
      );
    })
  );

  // Aplatizăm rezultatele și eliminăm duplicatele
  const results = scrapedArrays
    .flat()
    .filter(item => item && item.href && !seenLinks.has(item.href))
    .map(item => {
      seenLinks.add(item.href);
      return { ...item, source };
    });

  return results;
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
      // Șterge intrările mai vechi de 24 de ore și actualizează raportul
      const [deleteResult] = await connection.query(
        "DELETE FROM articles WHERE date < NOW() - INTERVAL 1 DAY"
      );
      report.deleted = deleteResult.affectedRows;

      // Parcurge fiecare sursă definită în sitesConfig
      for (const source in sitesConfig) {
        const { url, tags, cat } = sitesConfig[source];

        try {
          const page = await browser.newPage();
          await gotoWithRetry(page, url);

          const scrapedData = await scrapeTags(page, tags, source);
          report.totalScraped += scrapedData.length;

          if (scrapedData.length > 0) {
            // Extrage toate link-urile din datele scrape-uite
            const hrefs = scrapedData.map(item => item.href);

            // Obține toate articolele deja existente pentru link-urile respective
            const [existingRows] = await connection.query(
              "SELECT href FROM articles WHERE href IN (?)",
              [hrefs]
            );
            const existingHrefs = new Set(existingRows.map(row => row.href));

            // Separa articolele noi de cele existente
            const toInsert = [];
            scrapedData.forEach(item => {
              if (existingHrefs.has(item.href)) {
                report.skipped++;
                report.details.push({
                  action: "skipped",
                  reason: "Already exists",
                  item
                });
              } else {
                toInsert.push(item);
              }
            });

            // Inserare în masă pentru noile articole
            if (toInsert.length > 0) {
              const insertValues = toInsert.map(item => [
                item.source,
                item.text,
                item.href,
                item.imgSrc || null,
                cat
              ]);
              await connection.query(
                "INSERT INTO articles (source, text, href, imgSrc, cat) VALUES ?",
                [insertValues]
              );
              report.inserted += toInsert.length;
              toInsert.forEach(item => {
                report.details.push({ action: "inserted", item });
              });
            }
          }

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

    return res.json({
      message: "Scraping completed.",
      report
    });
  } catch (error) {
    console.error("Error in scraping:", error.message);
    return res.status(500).json({ error: "Scraping failed" });
  }
}
