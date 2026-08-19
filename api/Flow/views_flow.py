from rest_framework.generics import GenericAPIView, RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Flow.models_flow import Flow
from api.Channel.models_channel import Channle
from api.Flow.serializers_flow import SerializerFlows
import json, requests


class AddListFlows(GenericAPIView):
    
    permission_classes = [IsAuthenticated]
    serializer_class = SerializerFlows
    
    def post(self, request, channel_id):
        serializer = SerializerFlows(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        channel = get_object_or_404(Channle, channle_id=channel_id)
        flow_ = Flow.objects.create(
            account=channel.account_id, 
            flow=serializer.validated_data['flow'], 
            flow_name=serializer.validated_data['flow_name'],
        )
        channel.flows.add(flow_)
        channel.save()

        return Response(status=status.HTTP_200_OK)
    
    def get(self, request, channel_id):
        channel = get_object_or_404(Channle.objects.select_related('account_id'), channle_id=channel_id)
        flows = channel.flows.all().select_related('account')
        serializer = SerializerFlows(flows, many=True, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)


class SetDefaultFlow(GenericAPIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, channel_id):
        if 'is_default' not in request.GET:
            return Response({'error': 'is_default query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if 'flow_id' not in request.data:
            return Response({'error': 'flow_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            channel = Channle.objects.filter(channle_id=channel_id).first()
            if not channel:
                return Response({'error':'No Channle found'}, status=status.HTTP_404_NOT_FOUND)
            flows = channel.flows.all()
        except:
            return Response({"error":"Channel matching query does not exist"}, status=status.HTTP_404_NOT_FOUND)
        for flow in flows:
            if flow.id == request.data['flow_id']:
                flow.is_default = request.GET['is_default']
                flow.save()
            else:
                flow.is_default = 'False'
                flow.save()

        return Response(status=status.HTTP_200_OK)


class UpdateFlowView(GenericAPIView):
    serializer_class = SerializerFlows
    
    def put(self, request, pk):
        serializer = SerializerFlows(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        flow = get_object_or_404(Flow, id=pk)
        flow.flow_name = serializer.validated_data['flow_name']
        flow.flow = serializer.validated_data['flow']
        flow.save()
        serializer = SerializerFlows(flow, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RetrieveFlow(RetrieveDestroyAPIView):
    queryset = Flow.objects.all()
    serializer_class = SerializerFlows
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
