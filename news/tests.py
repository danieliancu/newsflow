import json
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from taxonomy.models import Category, KeywordRule, Topic

from .event_services import (
    generate_event,
    merge_semantically_equivalent_candidates,
    process_event_queue,
    reserve_event_budget,
    synchronize_events,
)
from .models import (
    Article,
    AutomaticUpdateLock,
    Event,
    EventArticle,
    EventBudget,
    RefreshRun,
    Source,
)
from .services import (
    assign_duplicate,
    canonicalize_url,
    classify_article,
    decode_response_text,
    extract_article,
    extract_image_url_from_html,
    ingest_source,
    near_duplicate_score,
)


class ExtractionTests(TestCase):
    def test_extracts_metadata_and_first_meaningful_paragraph(self):
        html = """
        <html><head>
          <link rel="canonical" href="/stire?utm_source=test">
          <meta property="og:title" content=" Titlu important ">
          <meta name="description" content="Șapoul știrii">
          <script type="application/ld+json">
            {"@type":"BreadcrumbList","itemListElement":[
              {"item":{"name":"HOME"}},{"item":{"name":"Știri"}},
              {"item":{"name":"Externe"}},{"item":{"name":"Rusia"}},
              {"item":{"name":"Titlu important"}}
            ]}
          </script>
        </head><body><article><h1>Titlu important</h1><p>Scurt.</p></article>
        <section>
          <p>Acesta este primul paragraf suficient de lung pentru a fi extras corect.</p>
          <p>Acesta este al doilea paragraf suficient de lung pentru a fi extras corect.</p>
        </section></body></html>
        """
        result = extract_article(html, "https://exemplu.ro/alta")
        self.assertEqual(result["canonical_url"], "https://exemplu.ro/stire")
        self.assertEqual(result["title"], "Titlu important")
        self.assertTrue(result["first_paragraph"].startswith("Acesta este"))
        self.assertNotIn("second_paragraph", result)
        self.assertEqual(result["source_sections"], ["Externe", "Rusia"])

    def test_canonical_url_removes_tracking_but_keeps_real_query(self):
        url = canonicalize_url("HTTPS://EXEMPLU.RO/stire/?id=2&utm_medium=social#fragment")
        self.assertEqual(url, "https://exemplu.ro/stire?id=2")

    def test_utf8_html_with_wrong_latin1_header_is_decoded_correctly(self):
        correct = "<title>Apărarea aeriană din Varșovia</title>"
        response = SimpleNamespace(
            encoding="ISO-8859-1",
            apparent_encoding="utf-8",
            content=correct.encode("utf-8"),
            text=correct.encode("utf-8").decode("latin-1"),
        )

        self.assertEqual(decode_response_text(response), correct)

    def test_extracts_og_image_before_twitter_image_and_resolves_relative_url(self):
        html = """
        <meta property="og:image" content="/media/principala.jpg">
        <meta name="twitter:image" content="https://cdn.example.ro/alternativa.jpg">
        """
        self.assertEqual(
            extract_image_url_from_html(html, "https://example.ro/stire/1"),
            "https://example.ro/media/principala.jpg",
        )

    def test_uses_twitter_image_and_rejects_unsafe_scheme(self):
        fallback_html = '<meta name="twitter:image" content="//cdn.example.ro/image.jpg">'
        unsafe_html = '<meta property="og:image" content="data:image/png;base64,abc">'
        self.assertEqual(
            extract_image_url_from_html(fallback_html, "https://example.ro/stire"),
            "https://cdn.example.ro/image.jpg",
        )
        self.assertEqual(
            extract_image_url_from_html(unsafe_html, "https://example.ro/stire"),
            "",
        )


@override_settings(OPENAI_CLASSIFICATION_ENABLED=False)
class ImageBackfillTests(TestCase):
    @patch("news.management.commands.backfill_article_images._can_fetch", return_value=True)
    @patch("news.management.commands.backfill_article_images.requests.Session")
    def test_backfill_updates_only_articles_without_images(self, session_class, can_fetch):
        source = Source.objects.create(
            name="Sursa imagini",
            domain="imagini.ro",
            feed_url="https://imagini.ro/rss",
        )
        missing = Article.objects.create(
            source=source,
            canonical_url="https://imagini.ro/lipsa",
            title="Fără imagine",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        existing = Article.objects.create(
            source=source,
            canonical_url="https://imagini.ro/existenta",
            title="Cu imagine",
            image_url="https://imagini.ro/deja.jpg",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        html = '<meta property="og:image" content="/noua.jpg">'
        response = Mock(
            encoding="utf-8",
            apparent_encoding="utf-8",
            content=html.encode(),
            text=html,
        )
        response.raise_for_status.return_value = None
        session_class.return_value.get.return_value = response
        output = StringIO()

        call_command("backfill_article_images", stdout=output)

        missing.refresh_from_db()
        existing.refresh_from_db()
        self.assertEqual(missing.image_url, "https://imagini.ro/noua.jpg")
        self.assertEqual(existing.image_url, "https://imagini.ro/deja.jpg")
        self.assertEqual(session_class.return_value.get.call_count, 1)
        self.assertIn("1 actualizate", output.getvalue())


@override_settings(OPENAI_CLASSIFICATION_ENABLED=False)
class ClassificationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Tehnologie", slug="tehnologie")
        self.topic = Topic.objects.create(
            category=self.category, name="Inteligență artificială", slug="inteligenta-artificiala"
        )
        KeywordRule.objects.create(topic=self.topic, phrase="inteligență artificială")
        self.source = Source.objects.create(
            name="Exemplu", domain="exemplu.ro", feed_url="https://exemplu.ro/rss"
        )

    def test_title_has_more_weight_than_paragraphs(self):
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://exemplu.ro/articol",
            title="Inteligență artificială în România",
            lead="Inteligență artificială pentru companii",
            first_paragraph="Un proiect de inteligență artificială a fost lansat.",
            second_paragraph="O soluție de inteligență artificială este testată.",
        )
        classify_article(article)
        match = article.topic_matches.get()
        self.assertEqual(match.score, 8)
        article.refresh_from_db()
        self.assertEqual(article.primary_category, self.category)

    def test_lowercase_romanian_ai_is_not_artificial_intelligence(self):
        KeywordRule.objects.create(topic=self.topic, phrase="ai")
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://exemplu.ro/ai-lumii",
            title="Ideologii lumii moderne",
            first_paragraph="Acesta este unul dintre principalii ideologi ai lumii moderne.",
        )
        classify_article(article)
        self.assertFalse(article.topic_matches.exists())
        article.refresh_from_db()
        self.assertIsNone(article.primary_category)

    def test_fencing_article_is_classified_as_sport(self):
        sport = Category.objects.create(name="Sport", slug="sport")
        fencing = Topic.objects.create(category=sport, name="Alte sporturi", slug="alte-sporturi")
        KeywordRule.objects.create(topic=fencing, phrase="scrimă")
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://exemplu.ro/scrima",
            title="Înfrângere dramatică pentru România la CM de scrimă",
            first_paragraph="Naționala masculină de sabie a României a fost învinsă.",
        )

        classify_article(article)

        article.refresh_from_db()
        self.assertEqual(article.primary_category, sport)

    def test_petroleum_industry_article_is_classified_as_economy(self):
        economy = Category.objects.create(name="Economie", slug="economie-petrol")
        energy = Topic.objects.create(category=economy, name="Energie", slug="energie-petrol")
        KeywordRule.objects.create(topic=energy, phrase="petrolieră")
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://exemplu.ro/industria-petroliera",
            title="Cum s-a născut industria petrolieră în Orientul Mijlociu",
            first_paragraph="Primul capitol a fost scris în munții Persiei.",
        )

        classify_article(article)

        article.refresh_from_db()
        self.assertEqual(article.primary_category, economy)

    def test_party_article_with_inflected_terms_is_classified_as_politics(self):
        politics = Category.objects.create(name="Politică", slug="politica-partide")
        parties = Topic.objects.create(
            category=politics,
            name="Partide și politică",
            slug="partide-si-politica",
        )
        KeywordRule.objects.create(topic=parties, phrase="PSD")
        KeywordRule.objects.create(topic=parties, phrase="PNL")
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://exemplu.ro/reforme-psd-pnl",
            title="Siegfried Mureșan (PNL): PSD a întârziat reformele",
            first_paragraph="Parlamentul a făcut ceea ce Guvernul nu a reușit.",
        )

        classify_article(article)

        article.refresh_from_db()
        self.assertEqual(article.primary_category, politics)


@override_settings(
    OPENAI_CLASSIFICATION_ENABLED=True,
    OPENAI_API_KEY="test-key",
    OPENAI_CLASSIFICATION_MODEL="gpt-5.4-nano",
    OPENAI_CLASSIFICATION_AUTO_THRESHOLD=0.80,
)
class AIClassificationTests(TestCase):
    def setUp(self):
        self.politics = Category.objects.create(name="Politică", slug="politica-ai")
        self.culture = Category.objects.create(name="Cultură", slug="cultura-ai")
        self.source = Source.objects.create(
            name="Sursa AI",
            domain="ai-example.ro",
            feed_url="https://ai-example.ro/rss",
        )

    @patch("news.ai_classifier.OpenAI")
    def test_high_confidence_ai_result_assigns_category_and_is_cached(self, openai_class):
        client = openai_class.return_value
        client.responses.create.return_value = Mock(
            output_text=json.dumps(
                {
                    "category": "Politică",
                    "confidence": 0.93,
                    "reason": "Articol despre activitatea unui partid politic.",
                }
            )
        )
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://ai-example.ro/articol",
            title="Un partid anunță o nouă strategie",
            first_paragraph="Conducerea formațiunii a prezentat planul.",
        )

        classify_article(article)
        classify_article(article)

        article.refresh_from_db()
        self.assertEqual(article.primary_category, self.politics)
        self.assertEqual(article.ai_suggested_category, self.politics)
        self.assertEqual(article.ai_confidence, 0.93)
        self.assertEqual(article.ai_model, "gpt-5.4-nano")
        self.assertEqual(client.responses.create.call_count, 1)
        call = client.responses.create.call_args.kwargs
        self.assertFalse(call["store"])
        self.assertEqual(call["text"]["format"]["type"], "json_schema")

    @patch("news.ai_classifier.OpenAI")
    def test_low_confidence_result_is_saved_without_assigning_pill(self, openai_class):
        openai_class.return_value.responses.create.return_value = Mock(
            output_text=json.dumps(
                {
                    "category": "Cultură",
                    "confidence": 0.52,
                    "reason": "Subiectul nu se potrivește clar unei categorii.",
                }
            )
        )
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://ai-example.ro/ambiguu",
            title="O poveste neobișnuită",
        )

        classify_article(article)

        article.refresh_from_db()
        self.assertIsNone(article.primary_category)
        self.assertEqual(article.ai_suggested_category, self.culture)
        self.assertEqual(article.ai_confidence, 0.52)

    @override_settings(OPENAI_API_KEY="")
    @patch("news.ai_classifier.OpenAI")
    def test_missing_api_key_skips_ai_without_failing_article(self, openai_class):
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://ai-example.ro/fara-cheie",
            title="Articol fără regulă",
        )

        classify_article(article)

        article.refresh_from_db()
        self.assertEqual(article.processing_status, Article.ProcessingStatus.PROCESSED)
        self.assertIsNone(article.primary_category)
        openai_class.assert_not_called()

    def test_breadcrumb_category_has_priority(self):
        international = Category.objects.create(name="Internațional", slug="international")
        russia = Topic.objects.create(category=international, name="Rusia", slug="rusia")
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://exemplu.ro/rusia",
            title="Analiză despre AI",
            source_sections=["Externe", "Rusia"],
        )
        classify_article(article)
        article.refresh_from_db()
        self.assertEqual(article.primary_category, international)
        self.assertTrue(article.topic_matches.filter(topic=russia).exists())

    def test_eu_farming_funds_are_economic_not_international(self):
        international = Category.objects.create(name="Internațional", slug="international")
        economy = Category.objects.create(name="Economie", slug="economie")
        eu_topic = Topic.objects.create(
            category=international, name="Uniunea Europeană", slug="uniunea-europeana"
        )
        KeywordRule.objects.create(topic=eu_topic, phrase="Uniunea Europeană")
        funds_topic = Topic.objects.create(
            category=economy, name="Fonduri europene", slug="fonduri-europene"
        )
        farming_topic = Topic.objects.create(
            category=economy, name="Agricultură", slug="agricultura"
        )
        KeywordRule.objects.create(topic=funds_topic, phrase="fonduri UE")
        KeywordRule.objects.create(topic=funds_topic, phrase="granturi")
        KeywordRule.objects.create(topic=farming_topic, phrase="fermieri")
        article = Article.objects.create(
            source=self.source,
            canonical_url="https://exemplu.ro/fonduri-ue",
            title="Fonduri UE 2026: granturi pentru ferme mici și tineri fermieri",
        )
        classify_article(article)
        article.refresh_from_db()
        self.assertEqual(article.primary_category, economy)
        self.assertFalse(article.topic_matches.filter(topic=eu_topic).exists())


class NearDuplicateTests(TestCase):
    def setUp(self):
        self.source_a = Source.objects.create(
            name="Sursa A", domain="a.ro", feed_url="https://a.ro/rss"
        )
        self.source_b = Source.objects.create(
            name="Sursa B", domain="b.ro", feed_url="https://b.ro/rss"
        )

    def test_paraphrased_titles_are_grouped(self):
        first = Article.objects.create(
            source=self.source_a,
            canonical_url="https://a.ro/1",
            title="UE l-a convocat pe însărcinatul cu afaceri al Rusiei la Bruxelles în legătură cu incursiunea dronelor ruseşti în România - Sursa A",
            lead="Uniunea Europeană l-a convocat pe însărcinatul cu afaceri al Moscovei după intrarea dronelor rusești în România.",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        second = Article.objects.create(
            source=self.source_b,
            canonical_url="https://b.ro/2",
            title="UE l-a convocat pe însărcinatul cu afaceri al Rusiei la Bruxelles, după incursiunea dronelor în spaţiul aerian al României",
            lead="Uniunea Europeană l-a convocat pe însărcinatul cu afaceri al Moscovei după intrarea dronelor rusești în România.",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        self.assertGreaterEqual(near_duplicate_score(first, second), 0.62)
        assign_duplicate(second)
        second.refresh_from_db()
        self.assertEqual(second.duplicate_of, first)

    def test_unrelated_titles_are_not_grouped(self):
        first = Article(source=self.source_a, title="Guvernul aprobă bugetul pentru educație")
        second = Article(source=self.source_b, title="Echipa națională câștigă meciul de fotbal")
        self.assertEqual(near_duplicate_score(first, second), 0)


@override_settings(NEWSFLOW_USER_AGENT="Newsflow-Test", NEWSFLOW_REQUEST_TIMEOUT=1)
class IngestionTests(TestCase):
    def test_duplicate_feed_entries_create_one_article(self):
        source = Source.objects.create(
            name="Exemplu", domain="exemplu.ro", feed_url="https://exemplu.ro/rss"
        )
        rss = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
        <item><title>Stire</title><link>https://exemplu.ro/stire?utm_source=x</link></item>
        <item><title>Stire</title><link>https://exemplu.ro/stire</link></item>
        </channel></rss>"""
        html = "<html><head><title>Știre test</title></head><body><article><p>Primul paragraf al știrii este suficient de lung pentru test.</p></article></body></html>"

        robots = Mock(ok=False)
        feed_response = Mock(content=rss)
        feed_response.raise_for_status.return_value = None
        page_response = Mock(text=html)
        page_response.raise_for_status.return_value = None
        session = Mock()
        session.get.side_effect = [robots, feed_response, page_response]

        with patch("news.services.requests.Session", return_value=session):
            count = ingest_source(source)
        self.assertEqual(count, 1)
        self.assertEqual(Article.objects.count(), 1)
        article = Article.objects.get()
        self.assertTrue(article.first_paragraph)
        self.assertEqual(article.lead, "")
        self.assertEqual(article.second_paragraph, "")
        self.assertEqual(article.author, "")

    def test_failed_article_is_retried(self):
        source = Source.objects.create(
            name="Exemplu", domain="exemplu.ro", feed_url="https://exemplu.ro/rss"
        )
        failed = Article.objects.create(
            source=source,
            canonical_url="https://exemplu.ro/stire",
            title="Stire",
            processing_status=Article.ProcessingStatus.FAILED,
            processing_attempts=1,
        )
        rss = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
        <item><title>Stire</title><link>https://exemplu.ro/stire</link></item>
        </channel></rss>"""
        html = "<html><head><title>Știre reparată</title></head><body><article><p>Primul paragraf al știrii este suficient de lung pentru test.</p></article></body></html>"
        robots = Mock(ok=False)
        feed_response = Mock(content=rss)
        feed_response.raise_for_status.return_value = None
        page_response = Mock(text=html)
        page_response.raise_for_status.return_value = None
        session = Mock()
        session.get.side_effect = [robots, feed_response, page_response]

        with patch("news.services.requests.Session", return_value=session):
            ingest_source(source)
        failed.refresh_from_db()
        self.assertEqual(failed.processing_status, Article.ProcessingStatus.PROCESSED)
        self.assertEqual(failed.processing_attempts, 2)


class EventPipelineTests(TestCase):
    def setUp(self):
        self.source_a = Source.objects.create(
            name="Sursa A",
            domain="a-eveniment.ro",
            feed_url="https://a-eveniment.ro/rss",
        )
        self.source_b = Source.objects.create(
            name="Sursa B",
            domain="b-eveniment.ro",
            feed_url="https://b-eveniment.ro/rss",
        )
        self.source_c = Source.objects.create(
            name="Sursa C",
            domain="c-eveniment.ro",
            feed_url="https://c-eveniment.ro/rss",
        )
        self.root = Article.objects.create(
            source=self.source_a,
            canonical_url="https://a-eveniment.ro/stire",
            title="Guvernul anunță un proiect important",
            first_paragraph="Guvernul a prezentat proiectul într-o conferință.",
            processing_status=Article.ProcessingStatus.PROCESSED,
            published_at=timezone.now(),
        )

    def _duplicate(self, source, suffix):
        return Article.objects.create(
            source=source,
            canonical_url=f"https://{source.domain}/{suffix}",
            title="Este anunțat proiectul important al Guvernului",
            first_paragraph="Proiectul a fost prezentat public astăzi.",
            processing_status=Article.ProcessingStatus.PROCESSED,
            published_at=timezone.now(),
            duplicate_of=self.root,
            duplicate_score=0.9,
        )

    def _semantic_event_candidates(self):
        article_b = self._duplicate(self.source_b, "codirlasu")
        radulescu_a = Article.objects.create(
            source=self.source_a,
            canonical_url="https://a-eveniment.ro/radulescu-fitch",
            title="Eugen Rădulescu avertizează după evaluarea Fitch",
            first_paragraph="Pericolul retrogradării ratingului României nu a trecut.",
            processing_status=Article.ProcessingStatus.PROCESSED,
            published_at=timezone.now(),
        )
        radulescu_c = Article.objects.create(
            source=self.source_c,
            canonical_url="https://c-eveniment.ro/radulescu-fitch",
            title="Eugen Rădulescu, despre evaluarea Fitch și riscurile pentru România",
            first_paragraph="Evaluarea Fitch menține riscurile pentru România.",
            processing_status=Article.ProcessingStatus.PROCESSED,
            published_at=timezone.now(),
        )
        first = Event.objects.create(
            title="Adrian Codirlașu comentează evaluarea Fitch ca pe un semn de înrăutățire",
            status=Event.Status.PENDING,
            last_article_at=timezone.now(),
        )
        second = Event.objects.create(
            title="Eugen Rădulescu, despre evaluarea Fitch și riscurile pentru România",
            status=Event.Status.PENDING,
            last_article_at=timezone.now(),
        )
        for article in (self.root, article_b):
            EventArticle.objects.create(event=first, article=article)
        for article in (radulescu_a, radulescu_c):
            EventArticle.objects.create(event=second, article=article)
        return first, second

    def test_synchronizes_multi_source_duplicates_into_one_event(self):
        self._duplicate(self.source_b, "stire")
        created, updated = synchronize_events()
        self.assertEqual((created, updated), (1, 0))
        event = Event.objects.get()
        self.assertEqual(event.articles.count(), 2)
        self.assertEqual(event.status, Event.Status.PENDING)

    def test_merges_separate_duplicate_clusters_for_same_story(self):
        self._duplicate(self.source_b, "prima-relatare")
        second_root = Article.objects.create(
            source=self.source_c,
            canonical_url="https://c-eveniment.ro/a-doua-relatare",
            title="Guvernul anunță un proiect important astăzi",
            first_paragraph="Guvernul a prezentat proiectul public.",
            processing_status=Article.ProcessingStatus.PROCESSED,
            published_at=timezone.now(),
        )
        Article.objects.create(
            source=self.source_a,
            canonical_url="https://a-eveniment.ro/a-doua-relatare",
            title="Guvernul anunță un proiect important după ședință",
            first_paragraph="Proiectul a fost prezentat public.",
            processing_status=Article.ProcessingStatus.PROCESSED,
            published_at=timezone.now(),
            duplicate_of=second_root,
            duplicate_score=0.9,
        )

        synchronize_events()

        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get()
        self.assertEqual(event.articles.count(), 4)
        self.assertEqual(event.status, Event.Status.PENDING)

    def test_daily_event_limit_blocks_only_event_generation(self):
        EventBudget.objects.create(max_new_events_per_day=1)
        Event.objects.create(
            title="Eveniment deja generat",
            first_generated_at=timezone.now(),
            last_article_at=timezone.now(),
        )
        candidate = Event.objects.create(
            title="Eveniment candidat", last_article_at=timezone.now()
        )
        reserved, amount, reason = reserve_event_budget(candidate)
        self.assertFalse(reserved)
        self.assertEqual(amount, 0)
        self.assertIn("zilnică", reason)

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("news.event_services.OpenAI")
    def test_generates_indexable_event_and_records_traceable_content(self, openai):
        article_b = self._duplicate(self.source_b, "stire")
        article_c = self._duplicate(self.source_c, "stire")
        event = Event.objects.create(
            title=self.root.title,
            status=Event.Status.PENDING,
            last_article_at=timezone.now(),
        )
        for article in (self.root, article_b, article_c):
            EventArticle.objects.create(event=event, article=article)
        original_slug = event.slug

        usage = SimpleNamespace(
            input_tokens=1000,
            output_tokens=300,
            total_tokens=1300,
            input_tokens_details=SimpleNamespace(cached_tokens=0),
        )
        extraction = SimpleNamespace(
            usage=usage,
            output_text=json.dumps(
                {
                    "claims": [
                        {"article_id": self.root.pk, "claim": "Proiectul a fost anunțat."},
                        {"article_id": article_b.pk, "claim": "Proiectul a fost anunțat."},
                    ]
                }
            ),
        )
        summary = SimpleNamespace(
            usage=usage,
            output_text=json.dumps(
                {
                    "title": "Proiectul anunțat de Guvern",
                    "summary": "O sinteză originală bazată pe relatările disponibile.",
                    "confirmed_facts": [
                        {
                            "text": "Proiectul a fost anunțat public.",
                            "article_ids": [self.root.pk, article_b.pk],
                        },
                        {
                            "text": "Afirmație dintr-o singură sursă.",
                            "article_ids": [article_c.pk],
                        },
                    ],
                    "differences": [],
                    "timeline": [],
                }
            ),
        )
        openai.return_value.responses.create.side_effect = [extraction, summary]

        self.assertTrue(generate_event(event))
        event.refresh_from_db()
        self.assertEqual(event.status, Event.Status.INDEXABLE)
        self.assertEqual(event.slug, original_slug)
        self.assertEqual(len(event.confirmed_facts), 1)
        self.assertEqual(event.ai_usage.count(), 2)
        self.assertGreater(event.total_cost_gbp, 0)
        summary_instructions = openai.return_value.responses.create.call_args_list[1].kwargs[
            "instructions"
        ]
        self.assertIn("focus pe informații", summary_instructions)
        self.assertIn("stil jurnalistic clar și fluent", summary_instructions)
        self.assertIn("Evită repetițiile, dramatizarea", summary_instructions)
        self.assertIn(
            "Titlul și summary trebuie să descrie exclusiv evenimentul",
            summary_instructions,
        )
        self.assertIn("fără nume de publicații", summary_instructions)
        self.assertIn("«informația este confirmată»", summary_instructions)
        self.assertIn("omite-l din summary", summary_instructions)
        self.assertNotIn("atribuirea explicită", summary_instructions)
        self.assertIn("diferă în mod real", summary_instructions)
        self.assertIn("returnează differences ca listă goală", summary_instructions)
        self.assertIn("3 milioane EUR", summary_instructions)

    def test_event_slug_is_immutable_after_creation(self):
        event = Event.objects.create(title="Titlul inițial")
        original_slug = event.slug

        event.title = "Un titlu complet diferit"
        event.slug = "slug-schimbat-manual"
        event.save()
        event.refresh_from_db()

        self.assertEqual(event.title, "Un titlu complet diferit")
        self.assertEqual(event.slug, original_slug)

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("news.event_services.OpenAI")
    def test_semantic_merge_combines_high_confidence_unpublished_events(self, openai):
        first, second = self._semantic_event_candidates()
        usage = SimpleNamespace(
            input_tokens=700,
            output_tokens=30,
            total_tokens=730,
            input_tokens_details=SimpleNamespace(cached_tokens=0),
        )
        openai.return_value.responses.create.return_value = SimpleNamespace(
            usage=usage,
            output_text=json.dumps({"same_event": True, "confidence": 0.95}),
        )

        self.assertEqual(merge_semantically_equivalent_candidates(), 1)
        self.assertEqual(Event.objects.count(), 1)
        survivor = Event.objects.get()
        self.assertEqual(survivor.pk, first.pk)
        self.assertEqual(survivor.articles.count(), 4)
        self.assertEqual(
            survivor.ai_usage.get().usage_type,
            "event_merge_check",
        )
        self.assertFalse(Event.objects.filter(pk=second.pk).exists())

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("news.event_services.OpenAI")
    def test_semantic_merge_leaves_uncertain_candidates_untouched(self, openai):
        first, second = self._semantic_event_candidates()
        usage = SimpleNamespace(
            input_tokens=700,
            output_tokens=30,
            total_tokens=730,
            input_tokens_details=SimpleNamespace(cached_tokens=0),
        )
        openai.return_value.responses.create.return_value = SimpleNamespace(
            usage=usage,
            output_text=json.dumps({"same_event": True, "confidence": 0.89}),
        )

        self.assertEqual(merge_semantically_equivalent_candidates(), 0)
        self.assertEqual(Event.objects.count(), 2)
        self.assertEqual(Event.objects.filter(pk__in=[first.pk, second.pk]).count(), 2)

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("news.event_services.OpenAI")
    def test_semantic_merge_never_checks_published_events(self, openai):
        first, second = self._semantic_event_candidates()
        first.first_generated_at = timezone.now()
        first.status = Event.Status.INDEXABLE
        first.save(update_fields=["first_generated_at", "status"])

        self.assertEqual(merge_semantically_equivalent_candidates(), 0)
        self.assertEqual(Event.objects.count(), 2)
        openai.assert_not_called()

    @patch("news.event_services.stabilize_old_events")
    @patch("news.event_services.merge_semantically_equivalent_candidates")
    def test_queue_checks_semantic_merges_before_building_generation_queue(
        self, semantic_merge, stabilize
    ):
        call_order = []
        semantic_merge.side_effect = lambda **kwargs: call_order.append("semantic")
        stabilize.side_effect = lambda: call_order.append("stabilize")

        process_event_queue()

        self.assertEqual(call_order, ["semantic", "stabilize"])

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("news.event_services.OpenAI")
    def test_skips_summary_update_when_new_source_has_no_significant_news(self, openai):
        article_b = self._duplicate(self.source_b, "stire")
        article_c = self._duplicate(self.source_c, "stire")
        generated_at = timezone.now() - timedelta(hours=2)
        event = Event.objects.create(
            title="Proiectul anunțat de Guvern",
            summary="Guvernul a anunțat proiectul.",
            status=Event.Status.GENERATED,
            first_generated_at=generated_at,
            last_generated_at=generated_at,
            generated_source_count=2,
            generation_count=1,
            source_snapshot=[
                {"id": self.root.pk, "source_id": self.source_a.pk},
                {"id": article_b.pk, "source_id": self.source_b.pk},
            ],
            last_article_at=timezone.now(),
        )
        for article in (self.root, article_b, article_c):
            EventArticle.objects.create(event=event, article=article)

        usage = SimpleNamespace(
            input_tokens=300,
            output_tokens=50,
            total_tokens=350,
            input_tokens_details=SimpleNamespace(cached_tokens=0),
        )
        openai.return_value.responses.create.return_value = SimpleNamespace(
            usage=usage,
            output_text=json.dumps(
                {
                    "should_update": False,
                    "change_types": [],
                    "reason": "Noua sursă repetă informațiile existente.",
                }
            ),
        )

        self.assertFalse(generate_event(event))
        event.refresh_from_db()
        self.assertEqual(openai.return_value.responses.create.call_count, 1)
        self.assertEqual(event.generation_count, 1)
        self.assertEqual(event.last_generated_at, generated_at)
        self.assertEqual(event.generated_source_count, 3)
        self.assertEqual(event.status, Event.Status.INDEXABLE)
        self.assertEqual(event.ai_usage.count(), 1)
        self.assertGreater(event.update_cost_gbp, 0)

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("news.event_services.OpenAI")
    def test_regenerates_summary_when_new_source_has_significant_news(self, openai):
        article_b = self._duplicate(self.source_b, "stire")
        article_c = self._duplicate(self.source_c, "stire")
        generated_at = timezone.now() - timedelta(hours=2)
        event = Event.objects.create(
            title="Proiectul anunțat de Guvern",
            summary="Guvernul a anunțat proiectul.",
            status=Event.Status.GENERATED,
            first_generated_at=generated_at,
            last_generated_at=generated_at,
            generated_source_count=2,
            generation_count=1,
            source_snapshot=[
                {"id": self.root.pk, "source_id": self.source_a.pk},
                {"id": article_b.pk, "source_id": self.source_b.pk},
            ],
            last_article_at=timezone.now(),
        )
        for article in (self.root, article_b, article_c):
            EventArticle.objects.create(event=event, article=article)

        usage = SimpleNamespace(
            input_tokens=500,
            output_tokens=100,
            total_tokens=600,
            input_tokens_details=SimpleNamespace(cached_tokens=0),
        )
        assessment = SimpleNamespace(
            usage=usage,
            output_text=json.dumps(
                {
                    "should_update": True,
                    "change_types": ["major_development"],
                    "reason": "Noua sursă anunță aprobarea proiectului.",
                }
            ),
        )
        extraction = SimpleNamespace(
            usage=usage,
            output_text=json.dumps(
                {
                    "claims": [
                        {"article_id": self.root.pk, "claim": "Proiectul a fost anunțat."},
                        {"article_id": article_c.pk, "claim": "Proiectul a fost aprobat."},
                    ]
                }
            ),
        )
        summary = SimpleNamespace(
            usage=usage,
            output_text=json.dumps(
                {
                    "title": "Proiectul Guvernului a fost aprobat",
                    "summary": "Proiectul anunțat anterior a fost aprobat.",
                    "confirmed_facts": [],
                    "differences": [],
                    "timeline": [],
                }
            ),
        )
        openai.return_value.responses.create.side_effect = [
            assessment,
            extraction,
            summary,
        ]

        self.assertTrue(generate_event(event))
        event.refresh_from_db()
        self.assertEqual(openai.return_value.responses.create.call_count, 3)
        self.assertEqual(event.generation_count, 2)
        self.assertGreater(event.last_generated_at, generated_at)
        self.assertEqual(event.title, "Proiectul Guvernului a fost aprobat")
        self.assertEqual(event.ai_usage.count(), 3)

    def test_automatic_command_skips_when_lock_is_active(self):
        AutomaticUpdateLock.objects.create(
            acquired_at=timezone.now(), owner="other-process"
        )
        call_command("automatic_news_update", stdout=StringIO())
        run = RefreshRun.objects.get()
        self.assertEqual(run.trigger, RefreshRun.Trigger.AUTOMATIC)
        self.assertEqual(run.status, RefreshRun.Status.SKIPPED)
