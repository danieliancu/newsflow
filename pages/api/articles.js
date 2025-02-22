import mysql from "mysql2/promise";
import dotenv from "dotenv";

dotenv.config(); // Încarcă fișierul .env.local

const pool = mysql.createPool({
  host: process.env.MYSQL_ADDON_HOST,
  user: process.env.MYSQL_ADDON_USER,
  password: process.env.MYSQL_ADDON_PASSWORD,
  database: process.env.MYSQL_ADDON_DB,
  port: process.env.MYSQL_ADDON_PORT,
  waitForConnections: true,
  connectionLimit: 10, // Crește limita conexiunilor simultane
  queueLimit: 0,       // Fără limită pentru coada de cereri
  acquireTimeout: 30000, // Timeout pentru obținerea conexiunii (60 secunde)
});

export const queryWithRetry = async (query, params = [], retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const [rows] = await pool.query(query, params);
      return rows;
    } catch (error) {
      if (i === retries - 1) throw error; // Re-aruncă eroarea la ultima încercare
      console.warn(`Retrying query, attempt ${i + 1}`);
    }
  }
};

console.log("MYSQL_ADDON_HOST:", process.env.MYSQL_ADDON_HOST);
console.log("MYSQL_ADDON_PORT:", process.env.MYSQL_ADDON_PORT);
console.log("MYSQL_ADDON_DB:", process.env.MYSQL_ADDON_DB);
console.log("MYSQL_ADDON_USER:", process.env.MYSQL_ADDON_USER);
console.log("MYSQL_ADDON_PASSWORD:", process.env.MYSQL_ADDON_PASSWORD);

// Crearea tabelei dacă nu există
const initializeDB = async () => {
    try {
      const connection = await pool.getConnection();
      console.log("Initializing database...");
      await connection.execute(
        `CREATE TABLE IF NOT EXISTS articles (
          id INT AUTO_INCREMENT PRIMARY KEY,
          source VARCHAR(50),
          text TEXT,
          href TEXT,
          imgSrc TEXT,
          label VARCHAR(255),
          cat VARCHAR(50),
          date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )`
      );
      connection.release();
      console.log("Database initialized successfully");
    } catch (error) {
      console.error("Failed to initialize database:", error.message);
      console.error(error.stack); // Log detaliat
    }
  };
  
// Initializează baza de date la pornirea serverului
initializeDB();

export default async function handler(req, res) {
  try {
    console.log("Fetching articles...");
    const { mode } = req.query;
    let rows;
    if (mode === 'initial') {
      // Fetch only the first 13 articles per category using a window function (MySQL 8+)
      const query = `
      SELECT id, source, text, href, imgSrc, label, cat, date FROM (
          SELECT *, ROW_NUMBER() OVER (PARTITION BY cat ORDER BY date DESC) as rn
          FROM articles
      ) as t
      WHERE rn <= 13
      ORDER BY date DESC
      `;
      const [initialRows] = await pool.query(query);
      rows = initialRows;
    } else {
      const [fullRows] = await pool.query("SELECT * FROM articles ORDER BY date DESC");
      rows = fullRows;
    }
    console.log("Articles fetched successfully:", rows.length);
    res.status(200).json({ data: rows });
  } catch (error) {
    console.error("Error fetching articles:", error.message);
    console.error(error.stack); // Log detaliat
    res.status(500).json({ error: `Failed to fetch articles: ${error.message}` });
  }
}
