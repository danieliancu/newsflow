import Head from "next/head";
import "@/styles/globals.css";

function App({ Component, pageProps }) {
  return (
    <>
    <Head>
      <title>Newsflow - Cele mai recente știri</title>
      <meta name="description" content="Newsflow.ro îți aduce cele mai recente știri din toate domeniile. Fii la curent cu actualitatea!" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <meta name="robots" content="index, follow" />
      <meta property="og:title" content="Newsflow - Cele mai recente știri" />
      <meta property="og:description" content="Newsflow.ro îți aduce cele mai recente știri din toate domeniile." />
      <meta property="og:image" content="/images/default.jpg" />
      <meta property="og:type" content="website" />
      <meta property="og:url" content="https://newsflow.ro" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content="Newsflow - Cele mai recente știri" />
      <meta name="twitter:description" content="Newsflow.ro îți aduce cele mai recente știri din toate domeniile." />
      <meta name="twitter:image" content="/images/default.jpg" />
      <link rel="canonical" href="https://newsflow.ro" />
    </Head>
      <Component {...pageProps} />
  </>
  );
}

export default App;
