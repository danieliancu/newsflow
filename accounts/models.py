from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Adresa de email este obligatorie.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff") or not extra_fields.get("is_superuser"):
            raise ValueError("Superutilizatorul trebuie să aibă drepturi complete.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class FeedMode(models.TextChoices):
        FOR_YOU = "for-you", "Pentru tine"
        LATEST = "latest", "Cele mai noi"

    class FeedDisplayMode(models.TextChoices):
        CARDS = "cards", "Carduri"
        COMPACT = "compact", "Compact"

    username = None
    email = models.EmailField("email", unique=True)
    last_feed_seen_at = models.DateTimeField(null=True, blank=True)
    feed_mode = models.CharField(
        max_length=10,
        choices=FeedMode.choices,
        default=FeedMode.FOR_YOU,
    )
    feed_display_mode = models.CharField(
        max_length=10,
        choices=FeedDisplayMode.choices,
        default=FeedDisplayMode.COMPACT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class CategoryPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="category_preferences")
    category = models.ForeignKey("taxonomy.Category", on_delete=models.CASCADE)
    weight = models.PositiveSmallIntegerField(default=1, choices=[(1, "Normal"), (2, "Important")])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "category"], name="unique_user_category_preference")
        ]

    def __str__(self):
        return f"{self.user.email} · {self.category.name}"


class TopicPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="topic_preferences")
    topic = models.ForeignKey("taxonomy.Topic", on_delete=models.CASCADE)
    weight = models.PositiveSmallIntegerField(default=1, choices=[(1, "Normal"), (2, "Important")])
    is_blocked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "topic"], name="unique_user_topic_preference")
        ]

    def __str__(self):
        return f"{self.user.email} · {self.topic.name}"


class SourcePreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="source_preferences")
    source = models.ForeignKey("news.Source", on_delete=models.CASCADE)
    weight = models.PositiveSmallIntegerField(default=1, choices=[(1, "Normal"), (2, "Preferată")])
    is_blocked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "source"], name="unique_user_source_preference")
        ]

    def __str__(self):
        return f"{self.user.email} · {self.source.name}"


class FollowedTerm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followed_terms")
    term = models.CharField(max_length=80)
    normalized_term = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("term",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "normalized_term"],
                name="unique_user_followed_term",
            )
        ]

    def __str__(self):
        return f"{self.user.email} · {self.term}"


class EmailChallenge(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = "login", "Autentificare"
        REGISTRATION = "registration", "Confirmare cont"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_challenges")
    token_hash = models.CharField(max_length=64)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    next_url = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    sent_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "created_at"), name="email_ch_user_created_idx"),
            models.Index(fields=("ip_address", "created_at"), name="email_ch_ip_created_idx"),
        ]

    def __str__(self):
        return f"{self.user.email} · {self.get_purpose_display()}"
