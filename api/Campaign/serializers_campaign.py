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
