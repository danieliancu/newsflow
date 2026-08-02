import json
from datetime import timedelta
from unittest.mock import ANY, patch

from django.test import TestCase, override_settings
from django.db.utils import OperationalError
from django.utils import timezone

from accounts.models import CategoryPreference, FollowedTerm, SourcePreference, TopicPreference, User
from news.models import Article, ArticleTopic, Event, EventArticle, RefreshRun, Source
from taxonomy.models import Category, Topic

from .models import Interaction, OpenedEvent, Recommendation, SavedEvent
from .services import ranked_feed


class FeedRankingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Economie", slug="economie")
        self.topic = Topic.objects.create(category=self.category, name="Energie", slug="energie")
        self.source = Source.objects.create(
            name="Sursa A", domain="a.ro", feed_url="https://a.ro/rss"
        )
        self.other_source = Source.objects.create(
            name="Sursa B", domain="b.ro", feed_url="https://b.ro/rss"
        )
        now = timezone.now()
        self.relevant = Article.objects.create(
            source=self.source,
            canonical_url="https://a.ro/energie",
            title="Energie",
            primary_category=self.category,
            published_at=now - timedelta(hours=2),
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        ArticleTopic.objects.create(article=self.relevant, topic=self.topic, score=5)
        self.other = Article.objects.create(
            source=self.other_source,
            canonical_url="https://b.ro/general",
            title="General",
            published_at=now,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        self.user = User.objects.create_user("user@example.ro", "parola-test-123")

    def test_preferences_rank_relevant_article_without_persisting_recommendations(self):
        CategoryPreference.objects.create(user=self.user, category=self.category, weight=2)
        result = ranked_feed(self.user)
        self.assertEqual(result[0], self.relevant)
        self.assertTrue(
            any(reason["type"] == "category" for reason in result[0].feed_reasons)
        )
        self.assertFalse(Recommendation.objects.exists())

    def test_blocked_source_and_hidden_article_are_excluded(self):
        SourcePreference.objects.create(user=self.user, source=self.source, is_blocked=True)
        Interaction.objects.create(user=self.user, article=self.other, kind=Interaction.Kind.HIDDEN)
        self.assertEqual(ranked_feed(self.user), [])

    def test_user_data_is_isolated(self):
        other_user = User.objects.create_user("other@example.ro", "parola-test-123")
        SourcePreference.objects.create(user=self.user, source=self.source, is_blocked=True)
        self.assertNotIn(self.relevant, ranked_feed(self.user))
        self.assertIn(self.relevant, ranked_feed(other_user))

    def test_user_without_preferences_gets_recent_articles_first(self):
        result = ranked_feed(self.user)
        self.assertEqual(result[0], self.other)

    @patch("recommendations.services.RANKING_CANDIDATE_LIMIT", 1)
    def test_preferred_source_is_included_before_candidate_limit(self):
        SourcePreference.objects.create(user=self.user, source=self.source)

        result = ranked_feed(self.user)

        self.assertIn(self.relevant, result)
        preferred_article = next(
            article for article in result if article.pk == self.relevant.pk
        )
        self.assertTrue(preferred_article.matches_preferences)

    def test_duplicate_article_is_not_shown(self):
        duplicate = Article.objects.create(
            source=self.other_source,
            canonical_url="https://b.ro/duplicat",
            title="Aceeași știre",
            duplicate_of=self.relevant,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        result = ranked_feed(self.user)
        self.assertNotIn(duplicate, result)

    def test_followed_topic_explains_recommendation(self):
        TopicPreference.objects.create(user=self.user, topic=self.topic)

        result = ranked_feed(self.user)

        self.assertEqual(result[0], self.relevant)
        self.assertEqual(result[0].feed_reason["type"], "topic")

    @patch("recommendations.services.RANKING_CANDIDATE_LIMIT", 1)
    def test_followed_term_matches_without_diacritics_and_enters_candidates(self):
        self.relevant.title = "Inteligența artificială schimbă energia"
        self.relevant.save(update_fields=["title"])
        FollowedTerm.objects.create(
            user=self.user,
            term="inteligenta artificiala",
            normalized_term="inteligenta artificiala",
        )

        result = ranked_feed(self.user)

        matched = next(article for article in result if article.pk == self.relevant.pk)
        self.assertTrue(matched.matches_preferences)
        self.assertEqual(matched.feed_reason["type"], "term")

    def test_latest_mode_is_chronological(self):
        SourcePreference.objects.create(user=self.user, source=self.source)

        result = ranked_feed(self.user, personalized=False)

        self.assertEqual(result[0], self.other)


class FeedInterfaceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Tehnologie", slug="tehnologie")
        self.topic = Topic.objects.create(
            category=self.category, name="Software", slug="software"
        )
        self.source = Source.objects.create(
            name="Sursa", domain="sursa.ro", feed_url="https://sursa.ro/rss"
        )
        self.article = Article.objects.create(
            source=self.source,
            canonical_url="https://sursa.ro/articol",
            title="Articol de test",
            primary_category=self.category,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        self.user = User.objects.create_user("ui@example.ro", "parola-test-123")
        self.client.force_login(self.user)

    def test_feed_has_desktop_and_mobile_preference_controls(self):
        response = self.client.get("/")
        self.assertContains(response, 'class="desktop-filters"')
        self.assertContains(response, 'class="mobile-filter-drawer"')
        self.assertContains(response, 'name="categories"', count=2)
        self.assertContains(response, 'class="category-menu"')
        self.assertContains(response, f'href="/category/{self.category.slug}/"')
        self.assertContains(response, 'name="topics"', count=2)
        self.assertContains(response, 'name="preferred_sources"', count=2)
        self.assertNotContains(response, "blocked_topics")
        self.assertContains(response, 'name="blocked_sources"', count=2)
        self.assertNotContains(response, 'class="category-arrow"')
        self.assertNotContains(response, "<summary>Topics</summary>")
        self.assertContains(response, 'class="feed-layout"')
        self.assertContains(response, 'class="story-meta-separator"', count=2)
        content = response.content.decode()
        self.assertLess(
            content.index('class="desktop-filters"'),
            content.index('class="homepage-events"') if 'class="homepage-events"' in content else len(content),
        )

    def test_story_card_displays_lazy_external_image(self):
        self.article.image_url = "https://cdn.example.ro/article.jpg"
        self.article.save(update_fields=["image_url"])

        response = self.client.get("/")

        self.assertContains(response, 'class="story-image"')
        self.assertContains(response, 'src="https://cdn.example.ro/article.jpg"')
        self.assertContains(response, 'loading="lazy"')
        self.assertContains(response, 'decoding="async"')

    def test_public_event_is_featured_and_linked_from_its_article(self):
        self.article.image_url = "https://cdn.example.ro/eveniment.jpg"
        self.article.save(update_fields=["image_url"])
        event = Event.objects.create(
            title="Eveniment important",
            status=Event.Status.INDEXABLE,
            summary="O sinteză verificată din mai multe surse.",
            generated_source_count=3,
            last_article_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        EventArticle.objects.create(event=event, article=self.article)

        response = self.client.get("/")

        self.assertNotContains(response, "Subiectele momentului")
        self.assertContains(response, "Eveniment")
        self.assertNotContains(response, event.summary)
        self.assertContains(response, event.title)
        self.assertContains(response, "Subiect din 3 surse")
        self.assertContains(response, f"/eveniment/{event.slug}/")
        self.assertContains(response, 'class="featured-event-image"')
        self.assertContains(response, self.article.image_url)

        archive = self.client.get("/evenimente/")
        self.assertContains(archive, 'class="event-archive-image"')
        self.assertContains(archive, self.article.image_url)

        detail = self.client.get(f"/eveniment/{event.slug}/")
        self.assertContains(detail, 'class="event-hero-image"')
        self.assertContains(detail, self.article.image_url)

        legacy_detail = self.client.get(f"/eveniment/{event.slug}-{event.pk}/")
        self.assertEqual(legacy_detail.status_code, 301)
        self.assertEqual(legacy_detail["Location"], f"/eveniment/{event.slug}/")

    def test_non_indexable_event_is_not_featured(self):
        event = Event.objects.create(
            title="Eveniment încă neconfirmat",
            status=Event.Status.GENERATED,
            summary="Are momentan numai două surse.",
            generated_source_count=2,
            last_article_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        EventArticle.objects.create(event=event, article=self.article)

        response = self.client.get("/")

        self.assertNotContains(response, event.title)

    def test_articles_from_same_public_event_are_grouped_in_feed(self):
        second_article = Article.objects.create(
            source=self.source,
            canonical_url="https://sursa.ro/al-doilea-articol",
            title="A doua relatare",
            primary_category=self.category,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        event = Event.objects.create(
            title="Poveste grupată",
            status=Event.Status.INDEXABLE,
            summary="O singură poveste din mai multe relatări.",
            generated_source_count=3,
            last_article_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        EventArticle.objects.create(event=event, article=self.article)
        EventArticle.objects.create(event=event, article=second_article)

        response = self.client.get("/?view=latest")

        displayed_ids = {article.pk for article in response.context["articles"]}
        self.assertEqual(len(displayed_ids & {self.article.pk, second_article.pk}), 1)

    def test_event_carousel_uses_five_latest_and_four_compact_cards(self):
        now = timezone.now()
        for index in range(9):
            Event.objects.create(
                title=f"Eveniment {index}",
                status=Event.Status.INDEXABLE,
                summary=f"Sinteză {index}",
                generated_source_count=3,
                last_article_at=now - timedelta(minutes=index),
                last_generated_at=now - timedelta(minutes=index),
            )

        response = self.client.get("/")

        self.assertContains(response, "data-carousel-slide aria-hidden", count=5)
        self.assertContains(response, "featured-event--compact", count=4)
        self.assertContains(response, "data-carousel-previous")
        self.assertContains(response, "data-carousel-next")
        self.assertContains(response, "show(index + 1, 1), 5000")

        latest_response = self.client.get("/?view=latest")
        self.assertContains(latest_response, "data-event-carousel")
        self.assertContains(latest_response, "Eveniment 0")

        for_you_response = self.client.get("/?view=for-you")
        self.assertContains(for_you_response, "data-event-carousel")
        self.assertContains(for_you_response, "Eveniment 0")

        filtered_response = self.client.get(
            "/", {"preferred_sources": [self.source.pk]}
        )
        self.assertContains(filtered_response, "data-event-carousel")
        self.assertContains(filtered_response, "Eveniment 0")

    def test_homepage_events_show_updated_date_after_new_public_activity(self):
        generated_at = timezone.now() - timedelta(hours=2)
        updated_at = timezone.now() - timedelta(minutes=5)
        event = Event.objects.create(
            title="Eveniment actualizat pe homepage",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică.",
            generated_source_count=4,
            first_generated_at=generated_at,
            last_generated_at=generated_at,
            last_article_at=updated_at,
        )

        response = self.client.get("/")

        self.assertContains(response, event.title)
        self.assertContains(response, "Actualizat acum 5\xa0minute")


    def test_archive_lists_only_public_events(self):
        public_event = Event.objects.create(
            title="Eveniment public",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică.",
            generated_source_count=3,
            last_article_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        Event.objects.create(
            title="Eveniment candidat",
            status=Event.Status.CANDIDATE,
            summary="Nu trebuie afișat.",
            last_article_at=timezone.now(),
        )

        response = self.client.get("/evenimente/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, public_event.title)
        self.assertNotContains(response, "Eveniment candidat")
        self.assertContains(response, "<h1>Subiectele zilei</h1>", html=True)
        self.assertContains(response, "1 subiect")

    def test_filter_only_shows_categories_with_available_articles(self):
        empty_category = Category.objects.create(name="Fără știri", slug="fara-stiri")

        response = self.client.get("/")

        self.assertContains(response, self.category.name, count=6)
        self.assertNotContains(response, empty_category.name)

    def test_preference_post_stores_only_selected_options(self):
        response = self.client.post(
            "/account/preferences/",
            {
                "categories": [self.category.pk],
                "preferred_sources": [self.source.pk],
            },
        )
        self.assertRedirects(response, "/")
        self.assertTrue(self.user.category_preferences.filter(category=self.category).exists())
        self.assertFalse(self.user.topic_preferences.exists())
        self.assertTrue(self.user.source_preferences.filter(source=self.source, is_blocked=False).exists())

        rendered = self.client.get("/")
        self.assertContains(
            rendered,
            '<details class="filter-section preference-group',
            count=10,
        )
        self.assertContains(
            rendered,
            '<input type="checkbox" data-group-toggle',
            count=8,
        )
        self.assertNotContains(rendered, "<details open")

    def test_preference_post_stores_free_followed_terms(self):
        response = self.client.post(
            "/account/preferences/",
            {
                "followed_terms": "Inteligență artificială, Dacia, dacia",
            },
        )

        self.assertRedirects(response, "/")
        self.assertEqual(
            list(self.user.followed_terms.values_list("term", flat=True)),
            ["Dacia", "Inteligență artificială"],
        )
        rendered = self.client.get("/")
        self.assertContains(rendered, "Termeni urmăriți", count=2)
        self.assertContains(rendered, 'data-term-value="Dacia"', count=2)

    def test_no_preferences_shows_all_articles(self):
        other = Article.objects.create(
            source=self.source,
            canonical_url="https://sursa.ro/alt-articol",
            title="Alt articol",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        response = self.client.get("/")
        self.assertIn(self.article, response.context["articles"])
        self.assertIn(other, response.context["articles"])
        self.assertEqual(response.context["other_articles"], [])
        self.assertFalse(Recommendation.objects.exists())
        self.assertFalse(
            Interaction.objects.filter(kind=Interaction.Kind.SHOWN).exists()
        )
        self.assertContains(response, "/interactions/shown/")

    def test_empty_personal_feed_links_to_latest_view(self):
        other_category = Category.objects.create(
            name="Categorie fără rezultate",
            slug="categorie-fara-rezultate",
        )
        CategoryPreference.objects.create(user=self.user, category=other_category)

        response = self.client.get("/")

        self.assertContains(response, 'class="empty"')
        self.assertContains(response, 'href="/?view=latest"')
        self.assertContains(response, "colectează știri noi")

    def test_shown_tracking_is_bulk_and_idempotent(self):
        other = Article.objects.create(
            source=self.source,
            canonical_url="https://sursa.ro/tracking",
            title="Tracking",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )

        first = self.client.post(
            "/interactions/shown/",
            {"article_ids": [self.article.pk, other.pk]},
            content_type="application/json",
        )
        second = self.client.post(
            "/interactions/shown/",
            {"article_ids": [self.article.pk, other.pk]},
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            Interaction.objects.filter(
                user=self.user, kind=Interaction.Kind.SHOWN
            ).count(),
            2,
        )

    def test_shown_tracking_rejects_large_payload_and_ignores_ineligible_articles(self):
        failed = Article.objects.create(
            source=self.source,
            canonical_url="https://sursa.ro/failed-tracking",
            title="Eșuat",
            processing_status=Article.ProcessingStatus.FAILED,
        )
        too_many = self.client.post(
            "/interactions/shown/",
            {"article_ids": list(range(1, 52))},
            content_type="application/json",
        )
        response = self.client.post(
            "/interactions/shown/",
            {"article_ids": [failed.pk]},
            content_type="application/json",
        )

        self.assertEqual(too_many.status_code, 400)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Interaction.objects.filter(
                user=self.user,
                article=failed,
                kind=Interaction.Kind.SHOWN,
            ).exists()
        )

    @patch(
        "recommendations.views.Interaction.objects.bulk_create",
        side_effect=OperationalError("database is locked"),
    )
    def test_shown_tracking_lock_is_non_fatal(self, bulk_create):
        response = self.client.post(
            "/interactions/shown/",
            {"article_ids": [self.article.pk]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"tracked": False})

    def test_ajax_save_hide_and_restore(self):
        saved = self.client.post(
            f"/article/{self.article.pk}/save/",
            HTTP_ACCEPT="application/json",
        )
        hidden = self.client.post(
            f"/article/{self.article.pk}/hide/",
            HTTP_ACCEPT="application/json",
        )
        restored = self.client.post(
            f"/article/{self.article.pk}/restore/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(saved.json()["saved_count"], 1)
        self.assertTrue(hidden.json()["hidden"])
        self.assertFalse(restored.json()["hidden"])
        self.assertFalse(
            Interaction.objects.filter(
                user=self.user,
                article=self.article,
                kind=Interaction.Kind.HIDDEN,
            ).exists()
        )

    def test_feed_modes_and_new_article_count(self):
        self.user.last_feed_seen_at = timezone.now() - timedelta(days=1)
        self.user.save(update_fields=["last_feed_seen_at"])

        personalized = self.client.get("/?view=for-you")
        latest = self.client.get("/?view=latest")

        self.assertEqual(personalized.context["feed_mode"], "for-you")
        self.assertEqual(latest.context["feed_mode"], "latest")
        self.assertEqual(latest.context["new_articles_count"], 1)

    def test_authenticated_feed_remembers_last_selected_mode(self):
        latest = self.client.get("/?view=latest")
        self.user.refresh_from_db()

        self.assertEqual(latest.context["feed_mode"], "latest")
        self.assertEqual(self.user.feed_mode, "latest")
        self.assertEqual(self.client.get("/").context["feed_mode"], "latest")

        for_you = self.client.get("/?view=for-you")
        self.user.refresh_from_db()

        self.assertEqual(for_you.context["feed_mode"], "for-you")
        self.assertEqual(self.user.feed_mode, "for-you")
        self.assertEqual(self.client.get("/").context["feed_mode"], "for-you")

    def test_invalid_feed_mode_does_not_replace_saved_mode(self):
        self.user.feed_mode = "latest"
        self.user.save(update_fields=["feed_mode"])

        response = self.client.get("/?view=invalid")
        self.user.refresh_from_db()

        self.assertEqual(response.context["feed_mode"], "latest")
        self.assertEqual(self.user.feed_mode, "latest")

    def test_recently_read_uses_last_open_time(self):
        other = Article.objects.create(
            source=self.source,
            canonical_url="https://sursa.ro/recent",
            title="Articol recent",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        self.client.get(f"/article/{self.article.pk}/open/")
        self.client.get(f"/article/{other.pk}/open/")
        self.client.get(f"/article/{self.article.pk}/open/")

        response = self.client.get("/recently-read/")

        self.assertEqual(response.context["articles"][0], self.article)

    def test_recently_read_includes_opened_events_by_last_open_time(self):
        older_event = Event.objects.create(
            title="Subiect deschis anterior",
            status=Event.Status.INDEXABLE,
            summary="Primul subiect deschis.",
            generated_source_count=3,
            first_generated_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        newer_event = Event.objects.create(
            title="Subiect deschis recent",
            status=Event.Status.INDEXABLE,
            summary="Al doilea subiect deschis.",
            generated_source_count=3,
            first_generated_at=timezone.now(),
            last_generated_at=timezone.now(),
        )

        self.client.get(older_event.public_path)
        self.client.get(newer_event.public_path)
        self.client.get(older_event.public_path)
        response = self.client.get("/recently-read/")

        self.assertEqual(response.context["events"], [older_event, newer_event])
        self.assertContains(response, "Subiectele zilei")
        self.assertContains(response, older_event.title)
        self.assertEqual(OpenedEvent.objects.filter(user=self.user).count(), 2)

    def test_event_card_uses_published_until_event_is_updated(self):
        generated_at = timezone.now()
        event = Event.objects.create(
            title="Subiect cu etichetă temporală",
            status=Event.Status.INDEXABLE,
            summary="Subiect pentru card.",
            generated_source_count=3,
            first_generated_at=generated_at,
            last_generated_at=generated_at,
        )

        published = self.client.get("/evenimente/")
        self.assertContains(published, "Publicat")
        self.assertNotContains(published, "Actualizat")

        event.last_generated_at = generated_at + timedelta(minutes=5)
        event.save(update_fields=["last_generated_at"])
        updated = self.client.get("/evenimente/")

        self.assertContains(updated, "Actualizat")

    def test_new_report_marks_event_updated_before_summary_regeneration(self):
        generated_at = timezone.now() - timedelta(hours=2)
        event = Event.objects.create(
            title="Subiect cu relatare nouă",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică.",
            generated_source_count=3,
            first_generated_at=generated_at,
            last_generated_at=generated_at,
            last_article_at=timezone.now(),
        )

        archive = self.client.get("/evenimente/")
        detail = self.client.get(event.public_path)

        self.assertContains(archive, "Actualizat")
        self.assertContains(detail, "Actualizat")

    def test_saved_page_and_navigation_count(self):
        Interaction.objects.create(
            user=self.user, article=self.article, kind=Interaction.Kind.SAVED
        )
        response = self.client.get("/saved/")
        self.assertContains(response, "Articol de test")
        self.assertContains(response, 'data-lucide="bookmark"')
        self.assertContains(response, 'class="account-icon-badge"')
        self.assertContains(response, ">1</span>")

    def test_removing_from_saved_page_returns_to_saved_page(self):
        Interaction.objects.create(
            user=self.user, article=self.article, kind=Interaction.Kind.SAVED
        )
        response = self.client.post(
            f"/article/{self.article.pk}/save/", {"next": "saved"}
        )
        self.assertRedirects(response, "/saved/")
        self.assertFalse(
            Interaction.objects.filter(
                user=self.user, article=self.article, kind=Interaction.Kind.SAVED
            ).exists()
        )

    def test_event_can_be_saved_and_appears_in_saved_page(self):
        event = Event.objects.create(
            title="Subiect AI salvat",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică pentru test.",
            generated_source_count=3,
            first_generated_at=timezone.now(),
            last_generated_at=timezone.now(),
        )

        saved = self.client.post(
            f"/event/{event.pk}/save/", HTTP_ACCEPT="application/json"
        )
        archive = self.client.get("/evenimente/")
        detail = self.client.get(event.public_path)
        saved_page = self.client.get("/saved/")

        self.assertTrue(saved.json()["saved"])
        self.assertTrue(SavedEvent.objects.filter(user=self.user, event=event).exists())
        self.assertContains(archive, 'icon-button is-active')
        self.assertContains(detail, "Salvat")
        self.assertContains(saved_page, "Subiect AI salvat")
        self.assertContains(saved_page, ">1</span>")

    def test_event_timeline_is_hidden_with_one_date_and_shown_with_two(self):
        event = Event.objects.create(
            title="Subiect cu cronologie",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică pentru cronologie.",
            generated_source_count=3,
            first_generated_at=timezone.now(),
            last_generated_at=timezone.now(),
            timeline=[
                {
                    "date": "2026-08-02",
                    "text": "Primul moment al evenimentului.",
                    "article_ids": [1],
                }
            ],
        )

        single_date = self.client.get(event.public_path)
        self.assertNotContains(single_date, "Cronologie")
        self.assertNotContains(single_date, "Primul moment al evenimentului.")

        event.timeline.append(
            {
                "date": "2026-08-03",
                "text": "Al doilea moment al evenimentului.",
                "article_ids": [2],
            }
        )
        event.save(update_fields=["timeline"])

        two_dates = self.client.get(event.public_path)
        self.assertContains(two_dates, "Cronologie")
        self.assertContains(two_dates, "Primul moment al evenimentului.")
        self.assertContains(two_dates, "Al doilea moment al evenimentului.")

    def test_event_hides_updated_label_when_generation_times_are_identical(self):
        generated_at = timezone.now()
        event = Event.objects.create(
            title="Subiect publicat o singură dată",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică fără actualizări ulterioare.",
            generated_source_count=3,
            first_generated_at=generated_at,
            last_generated_at=generated_at,
        )

        response = self.client.get(event.public_path)

        self.assertContains(response, "Publicat")
        self.assertNotContains(response, "Actualizat")

    def test_event_can_be_removed_from_saved_page(self):
        event = Event.objects.create(
            title="Subiect AI de eliminat",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică pentru test.",
            generated_source_count=3,
            first_generated_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        SavedEvent.objects.create(user=self.user, event=event)

        response = self.client.post(
            f"/event/{event.pk}/save/", {"next": "saved"}
        )

        self.assertRedirects(response, "/saved/")
        self.assertFalse(SavedEvent.objects.filter(user=self.user, event=event).exists())

    def test_preferences_split_matching_and_other_news(self):
        self.article.primary_category = self.category
        self.article.save(update_fields=["primary_category"])
        other = Article.objects.create(
            source=self.source,
            canonical_url="https://sursa.ro/alta",
            title="Știre fără categorie",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        CategoryPreference.objects.create(user=self.user, category=self.category)
        response = self.client.get("/")
        self.assertIn(self.article, response.context["articles"])
        self.assertNotIn(other, response.context["articles"])
        self.assertIn(other, response.context["other_articles"])
        self.assertContains(response, "Alte știri")

    def test_default_interface_language_is_romanian(self):
        response = self.client.get("/")
        self.assertContains(response, '<html lang="ro">')
        self.assertContains(response, "Preferințe")
        self.assertNotContains(response, 'class="language-switcher"')


class AnonymousFeedFilterTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Economie", slug="economie-anon")
        self.other_category = Category.objects.create(name="Sport", slug="sport-anon")
        self.topic = Topic.objects.create(
            category=self.category, name="Taxe", slug="taxe-anon"
        )
        self.other_topic = Topic.objects.create(
            category=self.other_category, name="Fotbal", slug="fotbal-anon"
        )
        self.source = Source.objects.create(
            name="Sursa anonimă", domain="anon.ro", feed_url="https://anon.ro/rss"
        )
        self.matching_article = Article.objects.create(
            source=self.source,
            canonical_url="https://anon.ro/economie",
            title="Articol economic",
            primary_category=self.category,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        self.other_article = Article.objects.create(
            source=self.source,
            canonical_url="https://anon.ro/sport",
            title="Articol sportiv",
            primary_category=self.other_category,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        ArticleTopic.objects.create(article=self.matching_article, topic=self.topic, score=5)
        ArticleTopic.objects.create(article=self.other_article, topic=self.other_topic, score=5)

    def test_anonymous_feed_displays_temporary_filters(self):
        response = self.client.get("/")
        self.assertContains(response, 'class="desktop-filters"')
        self.assertContains(response, 'class="site-footer"')
        for path in ["/about/", "/terms/", "/privacy/", "/cookies/", "/contact/"]:
            self.assertContains(response, f'href="{path}"')
        self.assertNotContains(response, "Filtrele nu se salvează.")
        self.assertContains(response, "Filtrează revista presei", count=2)
        for label in (
            "Publicații preferate", "Publicații ascunse", "Categorii urmărite",
            "Subiecte urmărite", "Termeni urmăriți",
        ):
            self.assertContains(response, label)
        self.assertContains(response, "Cont gratuit", count=6)
        self.assertContains(response, 'id="login-benefits-modal"')
        self.assertContains(response, "Creează fluxul meu personalizat", count=2)
        self.assertContains(response, "Transformă Newsflow în fluxul tău personal", count=2)
        self.assertNotContains(response, "Transformă GRATUIT Newsflow în fluxul tău personal")
        self.assertContains(response, "Am deja cont", count=3)
        self.assertContains(response, "Creează cont gratuit")
        self.assertNotContains(response, "Salvează preferințele într-un cont")
        self.assertNotContains(response, "Gratuit. Preferințele tale vor fi disponibile pe orice dispozitiv.")
        self.assertNotContains(response, '<details class="filter-section preference-group guest-filter-section" open>')
        self.assertNotContains(response, "newsflow-login-invite-seen")
        self.assertNotContains(response, "10000")
        self.assertContains(response, "guest-personalization.js")
        self.assertContains(response, 'data-login-modal-open')

    def test_anonymous_filter_hides_categories_without_articles(self):
        empty_category = Category.objects.create(name="Cultură", slug="cultura-anon")
        response = self.client.get("/")
        self.assertNotContains(response, empty_category.name)

    def test_anonymous_category_filter_limits_articles_without_saving(self):
        response = self.client.get("/", {"categories": self.category.slug})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.matching_article, response.context["articles"])
        self.assertNotIn(self.other_article, response.context["articles"])
        self.assertContains(response, '<meta name="robots" content="noindex,follow">', html=True)
        self.assertEqual(response.context["canonical_url"], "http://127.0.0.1:8000/")

    def test_technical_pages_are_separate_and_render_the_shared_footer(self):
        pages = {
            "/about/": "Despre Newsflow",
            "/terms/": "Termeni și condiții",
            "/privacy/": "Confidențialitate",
            "/cookies/": "Cookie-uri",
            "/contact/": "Contact",
        }

        for path, title in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f"<h1>{title}</h1>")
                self.assertContains(response, 'class="technical-page"')
                self.assertContains(response, 'class="site-footer"')
    def test_numeric_category_url_permanently_redirects_to_slug(self):
        response = self.client.get("/", {"categories": self.category.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["selected_category_ids"])

    def test_guest_filters_multiple_sources_and_combines_dimensions(self):
        other_source = Source.objects.create(
            name="Altă sursă", domain="alta-anon.ro", feed_url="https://alta-anon.ro/rss"
        )
        combined = Article.objects.create(
            source=other_source,
            canonical_url="https://alta-anon.ro/taxe",
            title="Taxe din altă sursă",
            primary_category=self.category,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        ArticleTopic.objects.create(article=combined, topic=self.topic, score=5)

        sources = self.client.get(
            "/", {"preferred_sources": [self.source.pk, other_source.pk]}
        )
        combined_filter = self.client.get(
            "/",
            {
                "preferred_sources": other_source.pk,
                "categories": self.category.slug,
                "topic": self.topic.slug,
            },
        )

        self.assertIn(self.matching_article, sources.context["articles"])
        self.assertIn(combined, sources.context["articles"])
        self.assertEqual(combined_filter.context["articles"], [combined])

    def test_guest_topic_is_validated_and_limited_to_first_active_topic(self):
        inactive = Topic.objects.create(
            category=self.category, name="Inactiv", slug="inactiv-anon", is_active=False
        )
        valid = self.client.get("/", {"topic": self.topic.slug})
        multiple = self.client.get(
            "/", [("topic", self.topic.slug), ("topic", self.other_topic.slug)]
        )
        invalid = self.client.get("/", {"topic": "nu-exista"})
        inactive_response = self.client.get("/", {"topic": inactive.slug})

        self.assertEqual(valid.context["articles"], [self.matching_article])
        self.assertEqual(multiple.context["articles"], [self.matching_article])
        self.assertEqual(multiple.context["selected_topic_ids"], {self.topic.pk})
        self.assertIsNone(invalid.context["selected_guest_topic"])
        self.assertIsNone(inactive_response.context["selected_guest_topic"])
        self.assertContains(valid, "Urmărești temporar")
        self.assertContains(valid, "Păstrează acest subiect")

    def test_guest_filters_do_not_create_persistent_preferences(self):
        self.client.get(
            "/",
            {
                "preferred_sources": self.source.pk,
                "categories": self.category.slug,
                "topic": self.topic.slug,
            },
        )
        self.assertFalse(CategoryPreference.objects.exists())
        self.assertFalse(SourcePreference.objects.exists())
        self.assertFalse(TopicPreference.objects.exists())
        self.assertFalse(FollowedTerm.objects.exists())
        self.assertFalse(Interaction.objects.exists())

    def test_guest_save_actions_use_contextual_modal_with_register_fallback(self):
        event = Event.objects.create(
            title="Subiect public pentru guest",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică.",
            generated_source_count=3,
            first_generated_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        EventArticle.objects.create(event=event, article=self.matching_article)

        feed = self.client.get("/")
        event_page = self.client.get(event.public_path)

        self.assertContains(feed, "Creează un cont gratuit pentru a salva această știre")
        self.assertContains(event_page, "Creează un cont gratuit pentru a salva acest subiect")
        self.assertContains(feed, 'href="/account/register/?next=')
        self.assertContains(event_page, 'data-login-modal-open')
        self.assertFalse(Interaction.objects.exists())
        self.assertFalse(SavedEvent.objects.exists())

    def test_source_filter_is_applied_before_global_feed_limit(self):
        newer_source = Source.objects.create(
            name="Sursa foarte nouă",
            domain="noua.ro",
            feed_url="https://noua.ro/rss",
        )
        Article.objects.bulk_create(
            [
                Article(
                    source=newer_source,
                    canonical_url=f"https://noua.ro/{index}",
                    title=f"Articol nou {index}",
                    processing_status=Article.ProcessingStatus.PROCESSED,
                )
                for index in range(55)
            ]
        )

        response = self.client.get("/", {"preferred_sources": self.source.pk})

        self.assertIn(self.matching_article, response.context["articles"])
        self.assertIn(self.other_article, response.context["articles"])


class SearchInterfaceTests(TestCase):
    def setUp(self):
        self.source = Source.objects.create(
            name="Publicație Economică",
            domain="cautare.ro",
            feed_url="https://cautare.ro/rss",
        )
        self.article = Article.objects.create(
            source=self.source,
            canonical_url="https://cautare.ro/inflatie",
            title="Inflația încetinește în România",
            first_paragraph="Prețurile au crescut mai lent în această lună.",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )

    def test_header_contains_search_form(self):
        response = self.client.get("/")
        self.assertContains(response, 'class="header-search"')
        self.assertContains(response, 'action="/search/"')
        self.assertContains(response, 'type="search"')
        self.assertContains(response, 'data-lucide="log-in"')
        self.assertContains(response, 'data-lucide="user-plus"')
        self.assertNotContains(response, ">Autentificare</a>")
        self.assertNotContains(response, ">Cont nou</a>")
        self.assertContains(response, 'class="news-update-status"')
        self.assertNotContains(response, 'class="refresh-button"')
        self.assertContains(response, 'class="news-update-status-icon')
        self.assertContains(response, 'data-lucide="refresh-cw"')

    @patch("recommendations.views.enqueue_refresh")
    def test_refresh_starts_background_job_and_returns_to_current_page(self, enqueue):
        response = self.client.post("/refresh/", {"next": "/search/?q=economie"})
        self.assertRedirects(
            response, "/search/?q=economie", fetch_redirect_response=False
        )
        refresh_run = RefreshRun.objects.get()
        self.assertEqual(refresh_run.status, RefreshRun.Status.RUNNING)
        enqueue.assert_called_once_with(refresh_run.pk)

    @patch("recommendations.views.ingest_source")
    def test_refresh_respects_recent_collection_cooldown(self, ingest):
        self.source.last_checked_at = timezone.now()
        self.source.save(update_fields=["last_checked_at"])
        response = self.client.post("/refresh/", {"next": "/"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        ingest.assert_not_called()

    def test_header_displays_latest_refresh_time(self):
        refreshed_at = timezone.now().replace(hour=9, minute=7)
        self.source.last_checked_at = refreshed_at
        self.source.save(update_fields=["last_checked_at"])
        response = self.client.get("/")
        self.assertContains(response, "Actualizat")
        self.assertContains(response, timezone.localtime(refreshed_at).strftime("%H:%M"))

    def test_refresh_rejects_get(self):
        self.assertEqual(self.client.get("/refresh/").status_code, 405)

    def test_search_finds_title_paragraph_and_source(self):
        for query in ("Inflația", "Prețurile", "Publicație Economică"):
            response = self.client.get("/search/", {"q": query})
            self.assertContains(response, self.article.title)
            self.assertEqual(response.context["page_obj"].paginator.count, 1)
            self.assertContains(response, "Înapoi la homepage")
            self.assertContains(response, '<meta name="robots" content="noindex,follow">', html=True)

    def test_search_is_insensitive_to_romanian_diacritics(self):
        for query in ("inflatia", "preturile", "publicatie economica"):
            response = self.client.get("/search/", {"q": query})
            self.assertContains(response, self.article.title)
            self.assertEqual(response.context["page_obj"].paginator.count, 1)

        plain_article = Article.objects.create(
            source=self.source,
            canonical_url="https://cautare.ro/stire-fara-diacritice",
            title="Stire despre Bucuresti",
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        response = self.client.get("/search/", {"q": "București"})
        self.assertContains(response, plain_article.title)

    def test_search_excludes_failed_and_duplicate_articles(self):
        failed = Article.objects.create(
            source=self.source,
            canonical_url="https://cautare.ro/esuat",
            title="Inflația articol eșuat",
            processing_status=Article.ProcessingStatus.FAILED,
        )
        Article.objects.create(
            source=self.source,
            canonical_url="https://cautare.ro/duplicat",
            title="Inflația articol duplicat",
            duplicate_of=self.article,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        response = self.client.get("/search/", {"q": "Inflația"})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertNotContains(response, failed.title)

    def test_search_finds_public_events_by_title_and_summary(self):
        event = Event.objects.create(
            title="Programul blindatelor COBRA II",
            status=Event.Status.INDEXABLE,
            summary="Ministerul Apărării a recepționat vehicule produse în România.",
            generated_source_count=5,
            first_generated_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        hidden_event = Event.objects.create(
            title="COBRA II candidat ascuns",
            status=Event.Status.CANDIDATE,
            summary="Acest rezultat nu este public.",
        )

        title_response = self.client.get("/search/", {"q": "COBRA II"})
        self.assertContains(title_response, event.title)
        self.assertContains(title_response, f"/eveniment/{event.slug}/")
        self.assertNotContains(title_response, hidden_event.title)
        self.assertEqual(title_response.context["events_count"], 1)

        summary_response = self.client.get("/search/", {"q": "recepționat"})
        self.assertContains(summary_response, event.title)

        normalized_response = self.client.get("/search/", {"q": "receptionat"})
        self.assertContains(normalized_response, event.title)

    def test_search_results_are_paginated(self):
        Article.objects.bulk_create(
            [
                Article(
                    source=self.source,
                    canonical_url=f"https://cautare.ro/economie-{index}",
                    title=f"Economie articol {index}",
                    processing_status=Article.ProcessingStatus.PROCESSED,
                )
                for index in range(25)
            ]
        )
        response = self.client.get("/search/", {"q": "Economie"})
        self.assertEqual(len(response.context["articles"]), 24)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)
        self.assertContains(response, 'data-lucide="arrow-right"')


@override_settings(APP_PUBLIC_URL="https://newsflow.example")
class SeoArchiveTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Economie SEO", slug="economie-seo")
        self.topic = Topic.objects.create(
            category=self.category, name="Energie SEO", slug="energie-seo"
        )
        self.source = Source.objects.create(
            name="Publicația SEO",
            domain="seo.ro",
            feed_url="https://seo.ro/rss",
        )
        yesterday = timezone.now() - timedelta(days=1)
        for index in range(26):
            article = Article.objects.create(
                source=self.source,
                canonical_url=f"https://seo.ro/articol-{index}",
                title=f"Articol SEO {index}",
                primary_category=self.category,
                published_at=yesterday,
                processing_status=Article.ProcessingStatus.PROCESSED,
            )
            ArticleTopic.objects.create(article=article, topic=self.topic, score=5)
        failed = Article.objects.create(
            source=self.source,
            canonical_url="https://seo.ro/esuat",
            title="Articol eșuat",
            primary_category=self.category,
            processing_status=Article.ProcessingStatus.FAILED,
        )
        Article.objects.create(
            source=self.source,
            canonical_url="https://seo.ro/duplicat",
            title="Articol duplicat",
            primary_category=self.category,
            duplicate_of=failed,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )

    def test_source_slug_is_generated(self):
        self.assertEqual(self.source.slug, "publicatia-seo")

    def test_archives_are_public_paginated_and_exclude_ineligible_articles(self):
        paths = (
            f"/category/{self.category.slug}/",
            f"/source/{self.source.slug}/",
            f"/topic/{self.topic.slug}/",
        )
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["page_obj"].paginator.count, 26)
            self.assertEqual(len(response.context["articles"]), 24)
            self.assertContains(
                response, '<meta name="robots" content="index,follow">', html=True
            )
            self.assertContains(response, '"@type": "CollectionPage"')
            self.assertContains(response, '"@type": "BreadcrumbList"')

    def test_archives_show_today_first_and_group_older_articles_by_day(self):
        today_article = Article.objects.get(title="Articol SEO 0")
        older_article = Article.objects.get(title="Articol SEO 1")
        today_article.published_at = timezone.now()
        today_article.save(update_fields=["published_at"])
        older_article.published_at = timezone.now() - timedelta(days=2)
        older_article.save(update_fields=["published_at"])

        paths = (
            f"/category/{self.category.slug}/",
            f"/source/{self.source.slug}/",
            f"/topic/{self.topic.slug}/",
        )
        for path in paths:
            response = self.client.get(path)
            content = response.content.decode()
            self.assertEqual(list(response.context["current_articles"]), [today_article])
            self.assertEqual(response.context["current_articles_count"], 1)
            self.assertContains(
                response,
                'class="other-news events-day-section archive-day-section"',
            )
            self.assertContains(response, 'class="events-page-grid archive-day-grid"')
            self.assertContains(response, 'class="story story--archive-card', count=25)
            self.assertContains(
                response,
                'class="personal-feed-toolbar events-day-toolbar"',
            )
            self.assertContains(
                response,
                timezone.localdate().strftime("%d"),
            )
            self.assertLess(
                content.index(today_article.title),
                content.index(older_article.title),
            )

    def test_paginated_archive_has_clean_self_canonical(self):
        archive_paths = (
            ("category", self.category.slug),
            ("source", self.source.slug),
            ("topic", self.topic.slug),
        )
        for archive_type, slug in archive_paths:
            path = f"/{archive_type}/{slug}/"
            first_page = self.client.get(path)
            second_page = self.client.get(path, {"page": 2, "tracking": "x"})

            self.assertContains(first_page, 'class="archive-heading"')
            self.assertContains(first_page, 'class="archive-count"')
            self.assertNotContains(second_page, 'class="archive-heading"')
            self.assertNotContains(second_page, 'class="archive-count"')
            self.assertNotContains(second_page, "Nu există încă articole astăzi.")
            self.assertContains(second_page, 'class="other-news events-day-section')
            self.assertContains(second_page, 'class="events-page-grid archive-day-grid"')
            self.assertContains(second_page, 'aria-label="Paginare"')
            self.assertEqual(
                second_page.context["canonical_url"],
                f"https://newsflow.example{path}?page=2",
            )

    def test_romanian_category_path_redirects_to_english_path(self):
        response = self.client.get(
            f"/categorie/{self.category.slug}/", {"page": 2}
        )
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response["Location"], f"/category/{self.category.slug}/?page=2"
        )

    def test_other_romanian_public_paths_redirect_to_english_paths(self):
        redirects = (
            (f"/sursa/{self.source.slug}/", f"/source/{self.source.slug}/"),
            (f"/subiect/{self.topic.slug}/", f"/topic/{self.topic.slug}/"),
            ("/cautare/?q=seo", "/search/?q=seo"),
            ("/salvate/", "/saved/"),
        )
        for old_path, new_path in redirects:
            response = self.client.get(old_path)
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response["Location"], new_path)

    def test_thin_archive_is_noindex(self):
        thin = Category.objects.create(name="Cultură SEO", slug="cultura-seo")
        Article.objects.create(
            source=self.source,
            canonical_url="https://seo.ro/cultura",
            title="Un singur articol",
            primary_category=thin,
            processing_status=Article.ProcessingStatus.PROCESSED,
        )
        response = self.client.get(f"/category/{thin.slug}/")
        self.assertContains(
            response, '<meta name="robots" content="noindex,follow">', html=True
        )

    def test_topic_archive_uses_standard_cards_and_only_todays_events(self):
        articles = list(
            Article.objects.filter(topic_matches__topic=self.topic).order_by("pk")[:2]
        )
        today_event = Event.objects.create(
            title="Subiectul de astăzi",
            status=Event.Status.INDEXABLE,
            summary="Sinteza subiectului publicat astăzi.",
            generated_source_count=3,
            first_generated_at=timezone.now(),
            last_generated_at=timezone.now(),
        )
        old_event = Event.objects.create(
            title="Subiectul de ieri",
            status=Event.Status.INDEXABLE,
            summary="Sinteza subiectului publicat ieri.",
            generated_source_count=3,
            first_generated_at=timezone.now() - timedelta(days=1),
            last_generated_at=timezone.now() - timedelta(days=1),
        )
        EventArticle.objects.create(event=today_event, article=articles[0])
        EventArticle.objects.create(event=old_event, article=articles[1])

        response = self.client.get(f"/topic/{self.topic.slug}/")

        self.assertContains(response, "Subiectul de astăzi")
        self.assertNotContains(response, "Subiectul de ieri")
        self.assertContains(response, 'class="event-archive-card"')
        self.assertContains(response, "surse distincte")
        self.assertContains(response, "Publicat")
        self.assertNotContains(response, "Actualizat")

    def test_filter_combinations_are_noindex(self):
        response = self.client.get(
            "/",
            {
                "categories": [self.category.slug, "alta"],
                "preferred_sources": self.source.pk,
            },
        )
        self.assertContains(
            response, '<meta name="robots" content="noindex,follow">', html=True
        )
        self.assertEqual(response.context["canonical_url"], "https://newsflow.example/")

    def test_homepage_has_one_h1_and_site_identity_structured_data(self):
        response = self.client.get("/")
        self.assertEqual(response.content.count(b"<h1"), 1)
        schema = json.loads(response.context["structured_data"])
        types = {item["@type"] for item in schema["@graph"]}
        self.assertTrue({"WebSite", "Organization", "CollectionPage"} <= types)
        organization = next(
            item for item in schema["@graph"] if item["@type"] == "Organization"
        )
        self.assertEqual(
            organization["logo"]["url"],
            "https://newsflow.example/static/favicon.svg",
        )

    @override_settings(PUBLIC_CONTACT_EMAIL="office@newsflow.ro")
    def test_contact_exposes_public_editorial_email(self):
        response = self.client.get("/contact/")
        self.assertContains(response, "mailto:office@newsflow.ro")

    def test_news_article_has_publisher_logo(self):
        event = Event.objects.create(
            title="Subiect SEO verificabil",
            status=Event.Status.INDEXABLE,
            summary="O sinteză suficientă pentru pagina publică.",
            generated_source_count=3,
            first_generated_at=timezone.now() - timedelta(hours=1),
            last_generated_at=timezone.now(),
        )
        response = self.client.get(event.public_path)
        schema = json.loads(response.context["structured_data"])
        article = next(
            item for item in schema["@graph"] if item["@type"] == "NewsArticle"
        )
        organization = next(
            item for item in schema["@graph"] if item["@type"] == "Organization"
        )
        self.assertEqual(article["publisher"]["@id"], organization["@id"])
        self.assertTrue(article["isAccessibleForFree"])
        self.assertIn("logo", organization)

    def test_sitemap_and_robots_use_public_url(self):
        sitemap = self.client.get("/sitemap.xml")
        self.assertContains(
            sitemap, f"https://newsflow.example/category/{self.category.slug}/"
        )
        self.assertContains(
            sitemap, f"https://newsflow.example/source/{self.source.slug}/"
        )
        self.assertContains(
            sitemap, f"https://newsflow.example/topic/{self.topic.slug}/"
        )
        self.assertNotContains(sitemap, "/search/")
        self.assertContains(sitemap, "https://newsflow.example/about/")
        self.assertContains(sitemap, "https://newsflow.example/contact/")

        robots = self.client.get("/robots.txt")
        self.assertContains(
            robots, "Sitemap: https://newsflow.example/sitemap.xml"
        )
        self.assertContains(
            robots, "Sitemap: https://newsflow.example/news-sitemap.xml"
        )

    def test_news_sitemap_contains_only_recent_public_events(self):
        recent = Event.objects.create(
            title="Eveniment recent & verificat",
            status=Event.Status.INDEXABLE,
            summary="Sinteză publică.",
            generated_source_count=3,
            first_generated_at=timezone.now() - timedelta(hours=2),
            last_generated_at=timezone.now(),
        )
        Event.objects.create(
            title="Eveniment vechi",
            status=Event.Status.INDEXABLE,
            summary="Sinteză veche.",
            generated_source_count=3,
            first_generated_at=timezone.now() - timedelta(days=3),
            last_generated_at=timezone.now() - timedelta(days=3),
        )

        response = self.client.get("/news-sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "xmlns:news=", status_code=200)
        self.assertContains(response, "Eveniment recent &amp; verificat")
        self.assertContains(response, recent.public_path)
        self.assertNotContains(response, "Eveniment vechi")
