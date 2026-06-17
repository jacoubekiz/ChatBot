from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Channel.models_channel import Channle
from api.Campaign.models_campaign import WhatsAppCampaign
from api.Campaign.serializers_campaign import CampaignsSerializer, CampaignSerializer_
import pandas as pd
import json
from ..tasks import send_whatsapp_campaign


class CreateListCampaignsView(GenericAPIView):
    serializer_class = CampaignsSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, channel_id):
        channel = get_object_or_404(Channle, channle_id=channel_id)
        campaigns = WhatsAppCampaign.objects.filter(account_id=channel.account_id)
        if not campaigns:
            return Response({'error':'No campaigns found'}, status=status.HTTP_200_OK)
        serializer_campaigns = self.get_serializer(campaigns, many=True)
        data = serializer_campaigns.data

        return Response(data, status=status.HTTP_200_OK)
    
    def post(self, request, channel_id):
        channel = get_object_or_404(Channle, channle_id=channel_id)
        data = request.data
        file = request.data['file']
        content_template = data.get('content_template')
        campaign_name = data.get('campaign_name')
        user = request.user
        whatsappcampaign = WhatsAppCampaign.objects.create(
                    account_id=channel.account_id,
                    name=campaign_name,
                    template_name=data.get('template_name'),
                    created_by=user,
                )
        df = pd.read_csv(file)
        data_e = {
            'channel':channel.channle_id, 
            'df':df.to_json(orient='records'), 
            'account':channel.account_id.account_id,
            'content_template': content_template,
            'user_id': user.id,
            'language_code': data.get('language_code'),
            'template_name': data.get('template_name'),
            'template_parameters': data.get('template_parameters'),
            'whatsappcampaign': whatsappcampaign.campaign_id
        }
        payload = json.dumps(data_e)
        send_whatsapp_campaign.delay(payload)
        return Response({'campaign_id': whatsappcampaign.campaign_id}, status=status.HTTP_201_CREATED)


class GetCampaignView(GenericAPIView):
    serializer_class = CampaignSerializer_
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id):
        campaign = get_object_or_404(WhatsAppCampaign, campaign_id=campaign_id)
        serializer_campaign = self.get_serializer(campaign)
        # data = serializer_campaign.data
        data = serializer_campaign.data
        return Response(data, status=status.HTTP_200_OK)
