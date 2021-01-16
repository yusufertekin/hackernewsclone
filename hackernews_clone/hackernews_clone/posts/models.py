from django.db import models


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
    sentiment_label = models.TextField()

    class Meta:
        ordering = ['rank']
        indexes = [
            models.Index(fields=['rank']),
        ]
