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
    </Head>
      <Component {...pageProps} />
  </>
  );
}

export default App;
