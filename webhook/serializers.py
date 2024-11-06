from rest_framework import serializers
from .models import *
class TestWebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestWebhook
        fields = '__all__'