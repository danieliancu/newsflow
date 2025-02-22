import mysql from "mysql2/promise";

// Configurarea pool-ului pentru conexiunea la baza de date
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

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Metodă nepermisă" });
  }

  const { email } = req.body;
  if (!email) {
    return res.status(400).json({ error: "Adresa de email lipsește" });
  }

  try {
    const connection = await pool.getConnection();
    try {
      // Verifică dacă emailul există deja
      const [existingRows] = await connection.query(
        "SELECT id FROM newsletter WHERE email = ?",
        [email]
      );
      if (existingRows.length > 0) {
        return res.status(200).json({
          message: "Emailul introdus există deja în baza noastră de date!",
          exists: true,
        });
      }

      // Inserează emailul nou
      const [result] = await connection.query(
        "INSERT INTO newsletter (email) VALUES (?)",
        [email]
      );
      return res.status(200).json({
        message: "Emailul a fost înregistrat! Vă mulțumim pentru abonare!",
        result,
        exists: false,
      });
    } finally {
      connection.release();
    }
  } catch (error) {
    console.error("Eroare la inserarea emailului:", error.message);
    return res.status(500).json({ error: "Abonarea la newsletter a eșuat" });
  }
}
