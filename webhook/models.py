from django.db import models

class TestWebhook(models.Model):
    test_text = models.CharField(max_length=50)
    name = models.CharField(max_length=20)

    def __str__(self) -> str:
        return self.test_text