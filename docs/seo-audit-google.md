# Audit SEO critic Newsflow — Google Search și Google News

Data auditului: 1 august 2026. Domeniul final nu este încă stabilit; verificarea a fost făcută pe aplicația locală și pe configurația de producție simulată `https://newsflow.example`.

## Verdict executiv

Newsflow nu poate fi declarat „100% conform Google”. Google nu certifică publicații și nu garantează indexarea, includerea în Google News sau afișarea rezultatelor îmbogățite nici atunci când implementarea este validă. După remedierile din acest audit, fundația tehnică este pregătită pentru lansare, însă acceptarea finală rămâne condiționată de un domeniu HTTPS real, măsurători Core Web Vitals, Search Console și de un proces editorial demonstrabil pentru sintezele automate.

Stările folosite sunt: **Conform**, **Parțial conform**, **Neconform**, **Neverificabil înainte de lansare**.

| Domeniu | Scor actual | Observație |
|---|---:|---|
| Technical SEO | 91/100 | Configurația de producție este securizată și validată; DNS, TLS și crawl real nu pot fi testate local. |
| On-page | 94/100 | Homepage are un H1 unic, canonicale curate, paginile private sunt `noindex`, iar titlurile respectă limita de 110 caractere. |
| Structured Data | 95/100 | `WebSite`, `Organization`, `NewsArticle` și `BreadcrumbList` sunt prezente; validarea Google pe URL public rămâne necesară. |
| Google News | 79/100 | News sitemap și metadatele sunt corecte; eligibilitatea editorială și includerea nu pot fi garantate. |
| Editorial Trust | 70/100 | Operatorul, automatizarea, sursele și corecturile sunt explicate în paginile editoriale; controlul editorial uman sistematic rămâne o recomandare, nu o cerință Google explicită. |
| Performance | Neverificabil | Nu există origine publică pentru Lighthouse/CrUX și nu pot fi măsurate LCP, INP și CLS reale. |

Scorurile sunt o grilă internă ponderată pentru prioritizare, nu scoruri acordate de Google.

## Matrice critică

| Criteriu | Stare | Severitate | Dovadă și impact Google | Remediere / acceptare |
|---|---|---|---|---|
| Domeniu public și canonicale | Parțial conform | Critic | Toate URL-urile absolute folosesc `APP_PUBLIC_URL`; local rămâne intenționat `127.0.0.1`. Un deploy greșit ar publica canonicale locale. | Check-ul `newsflow.E001` blochează producția fără origine HTTPS externă. Configurați domeniul real înainte de lansare. |
| HTTPS și Django deploy | Conform în configurația simulată | Critic | `DEBUG`, hosts, redirect SSL, cookie-uri secure și HSTS sunt controlate prin mediu. | `manage.py check --deploy` trebuie rulat cu valorile reale și să încheie fără avertismente relevante. HSTS preload trebuie activat numai dacă toate subdomeniile sunt permanent HTTPS. |
| Crawling și indexare | Conform | Critic | `robots.txt` permite crawling și declară ambele sitemapuri; căutarea, contul și combinațiile de filtre sunt `noindex`; arhivele subțiri sunt `noindex`. | Verificați după lansare cu URL Inspection și rapoartele Page Indexing. |
| Sitemap general | Conform | Ridicat | Include homepage, arhive eligibile, evenimente și paginile de transparență; exclude căutarea și conturile. | Trimiteți `/sitemap.xml` în Search Console. |
| News sitemap | Conform tehnic | Ridicat | Include doar evenimente publice din ultimele două zile, maximum 1.000, cu publicație, limbă, dată și titlu. | Trimiteți `/news-sitemap.xml`; monitorizați erorile și nu păstrați URL-uri mai vechi de două zile. |
| Homepage semantic | Conform | Ridicat | Există exact un `<h1>` descriptiv, fără modificarea aspectului vizual. | Păstrați un singur H1 și ierarhia H2/H3 la schimbări de design. |
| Identitatea publicației | Conform tehnic | Ridicat | Homepage publică `WebSite` și `Organization`, cu nume, operator legal, URL și logo local absolut. | Validați pe domeniul real în Schema.org Validator; folosiți același nume și logo pe toate suprafețele. |
| `NewsArticle` | Conform tehnic | Ridicat | Include headline, descriere, imagini când există, date, autor, publisher cu logo, citări și `isAccessibleForFree`. | Validați URL-uri reprezentative în Rich Results Test. Lipsa unei imagini nu invalidează schema, dar reduce eligibilitatea vizuală. |
| Breadcrumbs | Conform tehnic | Mediu | Evenimentele și arhivele publică `BreadcrumbList`; navigarea vizibilă corespunde. | Validați pe domeniul real. |
| Titluri | Conform | Mediu | Generarea nouă limitează titlurile la 110 caractere, iar cele două titluri istorice care depășeau limita au fost rescrise fără schimbarea URL-urilor. | Păstrați titlurile factuale, clare și sub 110 caractere. |
| Date și prospețime | Parțial conform | Ridicat | `datePublished` și `dateModified` sunt distincte și vizibile. Actualizarea automată poate schimba `dateModified`. | Modificați data doar când conținutul se schimbă material; evitați prospețimea artificială. |
| Autor, operator și contact | Parțial conform | Critic | Byline „Redacția Newsflow”, pagina Despre și operatorul legal sunt publice. Emailul este configurabil, iar producția este blocată dacă lipsește. | Furnizați un email editorial real și monitorizat. Recomandat: profil editorial cu responsabil și procedură de escaladare. |
| Transparența automatizării | Conform ca divulgare | Mediu | Pagina Despre explică generarea automată și limitele sintezelor, iar pagina Contact oferă canalul de corectare. Google nu impune o etichetă AI pe fiecare articol. | Păstrați explicația editorială și datele de contact accesibile; documentați intern verificările aplicate. |
| Conținut AI la scară | Parțial conform | Critic | Cele 88 de sinteze oferă grupare, comparații, fapte comune, diferențe și citări, deci există valoare adăugată. Totuși, generarea la scară fără QA uman poate intra în zona `scaled content abuse` dacă scopul sau rezultatul devine manipularea clasamentelor ori conținutul este inexact/neoriginal. | Introduceți eșantionare editorială, praguri de retragere, jurnal de corecții, verificarea afirmațiilor sensibile și metrici de eroare. Nu publicați automat loturi neverificate când calitatea scade. |
| Imagini | Parțial conform | Ridicat | Imaginile provin din publicațiile citate și pot eșua sau bloca hotlinking; schema le include numai când există. | Pentru lansare, folosiți o soluție legală și stabilă de cache/proxy/CDN, dimensiuni declarate, formate responsive și fallback. Confirmați drepturile de utilizare. |
| Legături și atribuiri | Conform | Ridicat | Relatările originale sunt listate și linkurile externe folosesc `rel="noopener"`; citările apar și în schema articolului. | Monitorizați linkurile moarte și diversitatea surselor. Nu prezentați sinteza ca relatare originală. |
| Core Web Vitals | Neverificabil înainte de lansare | Ridicat | Mediul local nu reproduce rețeaua, cache-ul, CDN-ul și traficul real. | Lansarea cere LCP ≤ 2,5 s, INP < 200 ms și CLS < 0,1 la percentila 75 pe mobil și desktop; testați Lighthouse/PageSpeed și apoi CrUX. |
| Search Console și Google News | Neverificabil înainte de lansare | Ridicat | Nu există proprietate publică, acces Googlebot, DNS sau TLS real. | Verificați proprietatea, trimiteți sitemapurile, inspectați URL-uri și urmăriți indexarea, rich results, manual actions și performanța News. |

## Priorități de lansare

### Blocante înainte de lansare

1. Configurați `APP_PUBLIC_URL=https://domeniul-real`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, un secret puternic și `PUBLIC_CONTACT_EMAIL=office@newsflow.ro`.
2. Rulați `manage.py check --deploy`; nu lansați cu erori, canonicale locale sau email editorial lipsă.
3. Confirmați că toate paginile de cont, căutare și stările private rămân `noindex` și nu apar în sitemap.
4. Recomandat: definiți responsabilul editorial și un proces proporțional de QA, corectare și retragere a sintezelor eronate; Google nu impune verificarea umană a fiecărei sinteze.
6. Măsurați homepage, arhivă și eveniment pe mobil/desktop; remediați orice depășire CWV.

### Primele 7 zile

1. Configurați Search Console, trimiteți ambele sitemapuri și inspectați homepage, o arhivă, un eveniment indexabil și unul `noindex`.
2. Rulați Rich Results Test pentru `NewsArticle` și breadcrumbs și Schema.org Validator pentru `WebSite`/`Organization`.
3. Urmăriți crawl errors, duplicate/canonical selection, pagini excluse și apariția în suprafața News.
4. Verificați zilnic emailul de corecturi, linkurile moarte și imaginile care nu se încarcă.

### Optimizări ulterioare

1. Publicați profiluri editoriale/autor, politică de corecturi și jurnal de modificări materiale.
2. Adăugați un pipeline stabil de imagini cu dimensiuni responsive și control juridic.
3. Auditați lunar eșantioane de sinteze pentru acuratețe, atribuire, diversitate și valoare adăugată.
4. Folosiți datele Search Console/CrUX pentru prioritizare; nu modificați conținutul doar pentru a simula prospețimea.

## Verificări efectuate

- `manage.py check`: fără probleme.
- 58 teste ale aplicației `recommendations`: toate trec.
- `manage.py check --deploy` cu origine HTTPS, hosts, secret și email de producție simulate: configurația este pregătită să treacă fără avertismente relevante.
- Sitemapurile sunt generate ca XML; testele verifică includerea arhivelor și paginilor de transparență, excluderea căutării și fereastra de două zile a news sitemapului.
- Baza locală la audit: 88 evenimente, niciunul fără sinteză sau dată inițială; după remediere nu mai există titluri peste 110 caractere.

## Surse Google folosite

- [Article structured data](https://developers.google.com/search/docs/appearance/structured-data/article)
- [Structured data guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)
- [Site names / WebSite](https://developers.google.com/search/docs/appearance/site-names)
- [Organization structured data](https://developers.google.com/search/docs/appearance/structured-data/organization)
- [Using generative AI content](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content)
- [Spam policies — scaled content abuse](https://developers.google.com/search/docs/essentials/spam-policies)
- [Google News content policies](https://support.google.com/news/publisher-center/answer/6204050)
- [Google News article best practices](https://support.google.com/news/publisher-center/answer/9607104)
- [Google News technical requirements](https://support.google.com/news/publisher-center/answer/9606708)
- [Sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
- [Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals)

## Concluzie de acceptare

Codul elimină blocantele tehnice confirmate, dar lansarea este acceptabilă numai când domeniul HTTPS real și emailul editorial sunt configurate, verificarea de deploy este curată, paginile private nu sunt indexabile, testele pe URL public trec și există control editorial real. Google News rămâne condiționat de calitatea și utilitatea publicației; validitatea tehnică singură nu este suficientă.
