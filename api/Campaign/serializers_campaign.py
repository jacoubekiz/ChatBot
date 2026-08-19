from rest_framework import serializers
from .models_campaign import WhatsAppCampaign, AnalyticsCampaign


class AnalyticsCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsCampaign
        fields = '__all__'

    def to_representation(self, instance):
        repre = super().to_representation(instance)
        repre['account_id'] = instance.account_id.name
        repre['campaign_id'] = instance.campaign_id.name
        repre['contact'] = instance.contact.name
        return repre


class CampaignSerializer_(serializers.ModelSerializer):
    analytics_campaign = AnalyticsCampaignSerializer(many=True, read_only=True, source='analyticscampaign_set')
    class Meta:
        model = WhatsAppCampaign
        fields = ['analytics_campaign']


class CampaignsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppCampaign
        fields = ['campaign_id', 'name', 'sent_count', 'failed_count', 'total_recipients', 'template_name', 'status']

        extra_kwargs = {
            'status':{'read_only':True},
        }


class CreateCampaignSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True, 
        help_text="CSV file containing recipient data", 
        error_messages={
            'required': 'CSV file is required',
            'invalid': 'Please upload a valid file',
            'empty': 'The uploaded file is empty'
        }
    )

    campaign_name = serializers.CharField(
        required=True, 
        max_length=255, 
        help_text="Name of the campaign",
        error_messages={
            'required': 'Campaign name is required',
            'blank': 'Campaign name cannot be blank',
            'max_length': 'Campaign name cannot exceed 255 characters'
        }
    )

    template_name = serializers.CharField(
        required=True,
        help_text="WhatsApp template name",
        error_messages={
            'required': 'Template name is required'
        }
    )

    language_code = serializers.CharField(
        required=True,
        help_text="Template language code (e.g., en, ar)",
        error_messages={
            'required': 'Language code is required'
        }
    )    
    content_template = serializers.CharField(required=False, allow_blank=True, help_text="Template content")
    template_parameters = serializers.JSONField(required=False, allow_null=True, help_text="Template parameters")
    
    def validate_language_code(self, value):
        valid_codes = ['en', 'ar', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja']
        if value.lower() not in valid_codes:
            raise serializers.ValidationError(f"Invalid language code. Must be one of: {valid_codes}")
        return value.lower()
