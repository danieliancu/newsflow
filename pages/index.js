import Head from "next/head";
import App from "../components/App";

export default function Home() {
  return (
    <>
      <Head>
        <title>Newsflow.ro | Știri ultima oră | Prima pagină</title>
        <meta
          name="description"
          content="Descoperă știrile de ultima oră și cele mai importante informații de pe prima pagină."
        />
        <meta name="keywords" content="Newsflow.ro, știri, ultima oră, știri România, prima pagină" />
        <meta name="author" content="Newsflow.ro" />
        <link rel="icon" href="/images/C2.svg" />
      </Head>
      <App />
    </>
  );
}
