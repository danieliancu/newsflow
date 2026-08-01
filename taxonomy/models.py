from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Topic(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)

    class Meta:
        ordering = ("category__name", "name")
        constraints = [models.UniqueConstraint(fields=["category", "name"], name="unique_topic_per_category")]

    def __str__(self):
        return f"{self.category}: {self.name}"


class KeywordRule(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="keyword_rules")
    phrase = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("phrase",)
        constraints = [
            models.UniqueConstraint(fields=["topic", "phrase"], name="unique_keyword_rule_per_topic")
        ]

    def __str__(self):
        return f"{self.phrase} → {self.topic}"
