"""Conținutul paginilor publice de informare Newsflow."""

COMPANY = (
    "GREEN HORIZON CONCEPTS S.R.L., cu sediul în București, Sector 3, "
    "Strada Idealului nr. 40, CUI 51006687, nr. de ordine în Registrul "
    "Comerțului J2024047618008, EUID ROONRC.J2024047618008"
)

TECHNICAL_PAGES = {
    "about": {
        "title": "Despre Newsflow",
        "description": "Cum colectează, organizează și sintetizează Newsflow știrile din publicații românești.",
        "intro": "Newsflow este o platformă românească de descoperire a știrilor, construită pentru a reuni relatările mai multor publicații într-o experiență clară și ușor de urmărit.",
        "sections": [
            ("Ce face Newsflow", "Colectăm automat titluri, fragmente, date de publicare și imagini disponibile prin fluxurile RSS sau paginile publice ale publicațiilor. Le organizăm pe categorii, subiecte și surse, iar accesarea unei relatări conduce la publicația care a realizat materialul."),
            ("Subiecte din mai multe surse", "Când mai multe publicații relatează aceeași situație, Newsflow le poate grupa într-un subiect. Pentru subiectele eligibile, sistemul generează o sinteză neutră, evidențiază informațiile confirmate de mai multe surse, diferențele dintre relatări și cronologia disponibilă. Sintezele sunt realizate automat și pot conține erori; relatările originale rămân sursa de referință."),
            ("Responsabilitate editorială", "„Redacția Newsflow” este semnătura editorială a platformei, operate de GREEN HORIZON CONCEPTS S.R.L. Ea indică responsabilitatea operatorului pentru publicarea, întreținerea și corectarea paginilor de subiect, nu preluarea autoratului relatărilor originale. Sintezele sunt generate automat din sursele indicate. Atunci când este identificată sau semnalată o eroare de grupare, atribuire ori sinteză, pagina este verificată prin raportare la relatările originale și poate fi corectată sau retrasă din afișarea publică. Solicitările de corectare pot fi transmise folosind datele din pagina Contact."),
            ("Un flux adaptat cititorului", "Utilizatorii își pot alege categoriile, subiectele, termenii și publicațiile preferate. Un cont permite salvarea articolelor, păstrarea istoricului de lectură și ascunderea conținutului sau a surselor care nu prezintă interes."),
            ("Relația cu publicațiile", "Newsflow nu înlocuiește presa și nu revendică materialele publicațiilor. Titlurile, fragmentele și imaginile aparțin surselor indicate, iar linkurile trimit către materialul complet. Platforma facilitează descoperirea și compararea relatărilor."),
            ("Operatorul platformei", f"Newsflow este operat de {COMPANY}."),
        ],
    },
    "terms": {
        "title": "Termeni și condiții",
        "description": "Regulile aplicabile utilizării platformei Newsflow și conținutului agregat.",
        "intro": "Acești termeni explică modul în care poate fi folosit Newsflow. Prin accesarea platformei, accepți regulile de mai jos.",
        "sections": [
            ("Serviciul oferit", "Newsflow colectează și organizează informații publice despre articole de presă și oferă linkuri către publicațiile originale. Funcțiile, sursele și frecvența actualizărilor pot fi modificate, suspendate sau întrerupte pentru mentenanță, securitate ori dezvoltarea serviciului."),
            ("Conținutul publicațiilor", "Drepturile asupra articolelor, imaginilor, mărcilor și materialelor externe aparțin titularilor indicați. Newsflow afișează informații de identificare și fragmente pentru descoperirea materialelor. Utilizatorul trebuie să respecte condițiile publicației accesate prin link."),
            ("Sinteze automate", "Sintezele subiectelor, clasificările și grupările sunt generate automat din informațiile colectate. Ele au rol informativ, pot fi incomplete sau inexacte și nu reprezintă consultanță juridică, medicală, financiară ori profesională. Pentru verificare trebuie consultate relatările originale și sursele oficiale."),
            ("Conturi și utilizare permisă", "Utilizatorul este responsabil pentru accesul la adresa sa de email și pentru activitatea contului. Sunt interzise accesarea neautorizată, perturbarea serviciului, colectarea automată abuzivă, transmiterea de cod malițios și folosirea platformei cu încălcarea legii sau a drepturilor altora."),
            ("Disponibilitate și răspundere", "Depunem eforturi rezonabile pentru funcționarea și actualizarea platformei, dar nu garantăm disponibilitatea neîntreruptă, prezența tuturor publicațiilor sau exactitatea fiecărei informații externe ori automate. În limitele permise de lege, operatorul nu răspunde pentru decizii luate exclusiv pe baza sintezelor sau pentru conținutul și disponibilitatea site-urilor terțe."),
            ("Operator și lege aplicabilă", f"Serviciul este furnizat de {COMPANY}. Termenii sunt guvernați de legea română, fără a limita drepturile obligatorii acordate consumatorilor."),
        ],
    },
    "privacy": {
        "title": "Confidențialitate",
        "description": "Cum sunt colectate, folosite și protejate datele personale în Newsflow.",
        "intro": "Această informare descrie datele prelucrate atunci când folosești Newsflow, motivele prelucrării și drepturile tale.",
        "sections": [
            ("Operatorul datelor", f"Operatorul este {COMPANY}."),
            ("Date prelucrate", "Pentru cont prelucrăm adresa de email, parola stocată într-o formă criptografică nereversibilă, confirmările de autentificare și datele tehnice necesare securității, inclusiv adresa IP folosită la solicitarea linkurilor de acces. Mai păstrăm preferințele, termenii urmăriți, articolele salvate, istoricul deschiderilor și conținutul ori sursele ascunse."),
            ("Scopuri și temeiuri", "Folosim datele pentru crearea și autentificarea contului, furnizarea fluxului personalizat și a funcțiilor solicitate — executarea serviciului cerut de utilizator. Prevenirea abuzurilor, securitatea, depanarea și protejarea platformei se bazează pe interesul legitim al operatorului. Dacă legea impune păstrarea sau comunicarea unor informații, prelucrarea se bazează pe obligația legală."),
            ("Personalizare automată", "Newsflow ordonează automat articolele folosind preferințele și interacțiunile contului. Această personalizare nu produce efecte juridice și nu ia decizii cu impact similar asupra utilizatorului. Clasificarea și sintezele AI folosesc fragmente de știri, fără intenția de a transmite identificatorii contului către model."),
            ("Furnizori și legături externe", "Putem utiliza furnizori tehnici pentru găzduire, email și servicii AI, limitați la datele necesare funcției respective și obligați prin măsuri contractuale adecvate. Accesarea imaginilor, fonturilor sau linkurilor externe poate transmite furnizorului respectiv informații tehnice obișnuite, precum adresa IP și tipul browserului."),
            ("Durata păstrării", "Datele contului și preferințele sunt păstrate cât timp contul există. La ștergerea contului, datele asociate sunt eliminate din sistemul activ, cu excepția informațiilor care trebuie păstrate temporar în copii de siguranță, pentru securitate sau pentru îndeplinirea unei obligații legale. Înregistrările tehnice sunt păstrate numai cât este necesar scopului lor."),
            ("Drepturile tale", "Poți solicita accesul la date, rectificarea, ștergerea, restricționarea, portabilitatea și opoziția, în condițiile Regulamentului (UE) 2016/679. Ai dreptul să depui o plângere la Autoritatea Națională de Supraveghere a Prelucrării Datelor cu Caracter Personal. Solicitările pot fi trimise operatorului la adresa poștală indicată în pagina Contact."),
        ],
    },
    "cookies": {
        "title": "Cookie-uri",
        "description": "Cookie-urile și stocarea locală folosite de Newsflow.",
        "intro": "Newsflow folosește tehnologii strict necesare pentru autentificare, securitate și funcționarea interfeței.",
        "sections": [
            ("Cookie de sesiune", "Cookie-ul de sesiune menține autentificarea și asociază în siguranță solicitările browserului cu sesiunea curentă. Este esențial pentru cont și expiră conform configurării de securitate sau la încheierea sesiunii."),
            ("Protecție CSRF", "Cookie-ul de securitate CSRF ajută la prevenirea trimiterii neautorizate a formularelor în numele utilizatorului. Este necesar pentru autentificare, preferințe, salvări și celelalte acțiuni efectuate în cont."),
            ("Stocare locală", "Browserul poate memora local dacă invitația de creare a contului a fost deja afișată. Această alegere rămâne pe dispozitiv și poate fi eliminată prin ștergerea datelor site-ului din browser."),
            ("Servicii externe", "Pagina poate încărca fonturi, iconuri și imaginile articolelor de pe serverele furnizorilor sau ale publicațiilor originale. Aceștia pot primi informații tehnice obișnuite ale conexiunii și pot aplica propriile politici. Newsflow nu folosește în prezent cookie-uri proprii pentru publicitate comportamentală sau analiză de marketing."),
            ("Controlul din browser", "Poți bloca sau șterge cookie-urile din setările browserului. Blocarea tehnologiilor esențiale poate împiedica autentificarea, salvarea preferințelor sau trimiterea formularelor."),
            ("Operator", f"Politica este publicată de {COMPANY}."),
        ],
    },
    "contact": {
        "title": "Contact",
        "description": "Datele operatorului Newsflow și informații pentru solicitări.",
        "intro": "Ne poți contacta pentru corecturi, întrebări despre platformă, protecția datelor sau solicitări din partea publicațiilor.",
        "sections": [
            ("Operatorul Newsflow", "GREEN HORIZON CONCEPTS S.R.L.\nSediu social: București, Sector 3, Strada Idealului nr. 40\nCUI: 51006687\nNr. Registrul Comerțului: J2024047618008\nEUID: ROONRC.J2024047618008"),
            ("Corecturi și conținut", "Dacă observi o asociere greșită, o sinteză inexactă, o atribuire incorectă sau un link nefuncțional, indică titlul și adresa paginii Newsflow. Verificarea se face prin raportare la materialele publicațiilor și la sursele oficiale disponibile."),
            ("Pentru publicații", "Reprezentanții publicațiilor pot solicita corectarea denumirii sau descrierii unei surse, actualizarea fluxului RSS, verificarea atribuirii, excluderea unui material ori discutarea modului de afișare a fragmentelor și imaginilor."),
            ("Protecția datelor", "Cererile privind accesul, rectificarea, ștergerea, restricționarea, portabilitatea sau opoziția pot fi adresate operatorului în scris, la sediul social. Pentru identificarea cererii, include date suficiente pentru localizarea contului, fără a trimite parola."),
            ("Comunicări oficiale", "Adresa electronică publică este afișată pe această pagină atunci când este configurată pentru mediul de producție. Comunicările juridice pot fi trimise și prin corespondență la sediul social indicat mai sus."),
        ],
    },
}
