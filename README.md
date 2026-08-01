# Newsflow

Newsflow este o aplicație Django care colectează știri prin RSS, extrage titlul,
șapoul și primul paragraf, apoi construiește un flux pe baza preferințelor
utilizatorului. Clasificarea este hibridă: reguli locale urmate de un fallback AI.

## Pornire locală

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_taxonomy
python manage.py seed_sources
python manage.py createsuperuser
python manage.py runserver
```

Deschide `http://127.0.0.1:8000/`. Sursele RSS se adaugă manual la
`http://127.0.0.1:8000/admin/`.

## Email și verificare în doi pași

Autentificarea și crearea contului necesită confirmarea unui link unic primit
prin email. În dezvoltare, linkul este afișat în terminalul în care rulează
serverul. Pentru trimitere reală, copiază `.env.example` ca `.env` și completează
datele SMTP. Configurația exemplu este compatibilă cu Resend SMTP.

## Clasificare AI

Clasificarea folosește mai întâi breadcrumb-urile și regulile locale. Numai
articolele rămase fără categorie sunt trimise către OpenAI. Copiază
`.env.example` ca `.env` și completează `OPENAI_API_KEY`; cheia nu trebuie
adăugată niciodată în cod sau în Git. Modelul implicit este `gpt-5.4-nano`, iar
o categorie este aplicată automat numai la o încredere de minimum `0.80`.

Pentru a clasifica articolele deja existente după adăugarea cheii:

```powershell
python manage.py reclassify_news
```

## Colectare

Sursele initiale sunt adaugate cu `python manage.py seed_sources`. Surse
suplimentare pot fi adaugate din administrare. Pentru colectare:

```powershell
python manage.py collect_news
```

Articolele cu formulari diferite despre acelasi eveniment sunt grupate automat.
Pentru a reevalua toate articolele existente:

```powershell
python manage.py deduplicate_news
```

După modificarea regulilor sau a taxonomiei:

```powershell
python manage.py reclassify_news
```

Pentru o singură sursă:

```powershell
python manage.py collect_news --source 1
```

Comanda poate fi programată cu Windows Task Scheduler sau cron. Înainte de
folosirea unei surse în producție, verifică termenii publicației, politica
`robots.txt` și dreptul de a afișa fragmentele colectate.

## Actualizare automată și evenimente

Fluxul automat colectează știrile, aplică clasificarea și actualizează
evenimentele multi-sursă eligibile:

```powershell
python manage.py automatic_news_update
```

Pentru instalarea task-ului Windows care rulează o dată pe oră, deschide
PowerShell cu drepturi de administrator și rulează:

```powershell
.\scripts\install-hourly-task.ps1
```

Task-ul nu pornește o instanță nouă dacă rularea anterioară este încă activă.
Aplicația folosește suplimentar un lock în baza de date. Limitele de evenimente,
bugetele zilnice/lunare și costul maxim per eveniment se configurează în
`/admin/news/eventbudget/`. Atingerea limitei oprește numai generarea AI a
evenimentelor; colectarea și clasificarea știrilor continuă.

Evenimentele cu două surse sunt accesibile cu `noindex`, iar cele cu minimum
trei surse pot deveni indexabile. Evenimentele fără actualizări timp de șapte
zile devin stabile și nu mai generează costuri AI.

## Verificare

```powershell
python manage.py check
python manage.py test
```
