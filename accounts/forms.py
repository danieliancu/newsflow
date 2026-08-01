from django import forms
from django.contrib.auth.forms import UserCreationForm
import unicodedata

from taxonomy.models import Category, Topic
from news.models import Source

from .models import CategoryPreference, FollowedTerm, SourcePreference, TopicPreference, User


def normalize_followed_term(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return " ".join(value.split())


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class EmailPasswordLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Parolă", strip=False, widget=forms.PasswordInput)

    error_messages = {
        "invalid_login": "Emailul sau parola nu sunt corecte.",
    }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        if not email or not password:
            return cleaned_data
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user = None
        if user is None or not user.check_password(password):
            raise forms.ValidationError(self.error_messages["invalid_login"], code="invalid_login")
        cleaned_data["user"] = user
        return cleaned_data


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Parola actuală",
        strip=False,
        widget=forms.PasswordInput,
    )
    confirmation = forms.BooleanField(
        label="Înțeleg că ștergerea contului este definitivă.",
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Parola introdusă nu este corectă.")
        return password


class PreferenceForm(forms.Form):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )
    preferred_sources = forms.ModelMultipleChoiceField(
        queryset=Source.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )
    topics = forms.ModelMultipleChoiceField(
        queryset=Topic.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )
    blocked_sources = forms.ModelMultipleChoiceField(
        queryset=Source.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )
    followed_terms = forms.CharField(required=False)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        categories = Category.objects.order_by("name")
        sources = Source.objects.filter(is_active=True).order_by("name")
        topics = Topic.objects.filter(is_active=True).select_related("category").order_by(
            "category__name", "name"
        )
        self.fields["categories"].queryset = categories
        self.fields["preferred_sources"].queryset = sources
        self.fields["topics"].queryset = topics
        self.fields["blocked_sources"].queryset = sources

        if not self.is_bound:
            self.initial.update(
                categories=list(user.category_preferences.values_list("category_id", flat=True)),
                preferred_sources=list(
                    user.source_preferences.filter(is_blocked=False).values_list("source_id", flat=True)
                ),
                topics=list(
                    user.topic_preferences.filter(is_blocked=False).values_list("topic_id", flat=True)
                ),
                blocked_sources=list(
                    user.source_preferences.filter(is_blocked=True).values_list("source_id", flat=True)
                ),
                followed_terms=", ".join(user.followed_terms.values_list("term", flat=True)),
            )

    def clean_followed_terms(self):
        raw_value = self.cleaned_data.get("followed_terms", "")
        values = raw_value.replace("\r", "\n").replace(";", ",").replace("\n", ",").split(",")
        terms = []
        seen = set()
        for value in values:
            term = " ".join(value.strip().split())
            if not term:
                continue
            if len(term) < 3:
                raise forms.ValidationError("Fiecare termen trebuie să aibă minimum 3 caractere.")
            if len(term) > 80:
                raise forms.ValidationError("Un termen poate avea maximum 80 de caractere.")
            normalized = normalize_followed_term(term)
            if normalized not in seen:
                seen.add(normalized)
                terms.append((term, normalized))
        if len(terms) > 20:
            raise forms.ValidationError("Poți urmări maximum 20 de termeni.")
        return terms

    def save(self):
        CategoryPreference.objects.filter(user=self.user).delete()
        TopicPreference.objects.filter(user=self.user).delete()
        SourcePreference.objects.filter(user=self.user).delete()
        FollowedTerm.objects.filter(user=self.user).delete()

        for category in self.cleaned_data["categories"]:
            CategoryPreference.objects.create(user=self.user, category=category)
        for source in self.cleaned_data["preferred_sources"]:
            SourcePreference.objects.create(user=self.user, source=source)
        for source in self.cleaned_data["blocked_sources"]:
            SourcePreference.objects.update_or_create(
                user=self.user,
                source=source,
                defaults={"is_blocked": True},
            )
        for topic in self.cleaned_data["topics"]:
            TopicPreference.objects.create(user=self.user, topic=topic)
        FollowedTerm.objects.bulk_create(
            [
                FollowedTerm(user=self.user, term=term, normalized_term=normalized)
                for term, normalized in self.cleaned_data["followed_terms"]
            ]
        )
