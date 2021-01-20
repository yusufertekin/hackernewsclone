from datetime import datetime, timezone

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django_celery_beat.models import PeriodicTask


class Post(models.Model):
    id = models.IntegerField(primary_key=True)
    rank = models.IntegerField()
    subject = models.TextField()
    url = models.TextField()
    age = models.CharField(max_length=15)
    score = models.IntegerField(null=True, blank=True)
    submitted_by = models.CharField(max_length=15, null=True, blank=True)
    num_of_comments = models.IntegerField(null=True, blank=True)
    sentiment_score = models.FloatField(null=True, blank=True)
    sentiment_label = models.TextField(default="Not Ready")

    class Meta:
        ordering = ["rank"]
        indexes = [
            models.Index(fields=["rank"]),
        ]


class BaseTracker(models.Model):
    """Keeps track of update with hackernews.
    """
    IDLE = "idle"
    ACTIVE = "active"
    FAILED = "failed"
    STATUS_CHOICES = [
        (IDLE, "Idle"),
        (ACTIVE, "Active"),
        (FAILED, "Failed"),
    ]

    periodic_task = models.OneToOneField(PeriodicTask, on_delete=models.CASCADE)
    status = models.CharField(max_length=7, choices=STATUS_CHOICES, default=IDLE)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_finish_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def activate(cls):
        with transaction.atomic():
            st = (
                cls.objects.select_related("periodic_task")
                .select_for_update()
                .get(pk=1)
            )
            st.status = cls.ACTIVE
            st.last_run_at = datetime.now(tz=timezone.utc)
            st.save(update_fields=["status", "last_run_at"])

    @classmethod
    def finish(cls):
        with transaction.atomic():
            st = cls.objects.select_for_update().get(pk=1)
            st.status = cls.IDLE
            st.last_run_finish_at = datetime.now(tz=timezone.utc)
            st.save(update_fields=["status", "last_run_finish_at"])

    @classmethod
    def fail(cls):
        with transaction.atomic():
            st = cls.objects.select_for_update().get(pk=1)
            st.status = cls.FAILED
            st.last_run_finish_at = datetime.now(tz=timezone.utc)
            st.save(update_fields=["status", "last_run_finish_at"])

    def save(self, *args, **kwargs):
        if not self.pk and self.__class__.objects.exists():
            raise ValidationError(f"There can be only one {self.__name__} instance")
        # If periodic task is not enabled, it's not allowing us to update last_run_at field
        # that's why ScrapperTracker has its own last_run_at sync with PeriodicTask when possible
        if self.periodic_task.enabled:
            self.periodic_task.last_run_at = self.last_run_at
            self.periodic_task.save(update_fields=["last_run_at"])
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_status_display()}-{self.periodic_task}"


class ScrapperTracker(BaseTracker):
    class Meta(BaseTracker.Meta):
        db_table = "scrapper_tracker"


class APIFetcherTracker(BaseTracker):
    class Meta(BaseTracker.Meta):
        db_table = "api_fetcher_tracker"
