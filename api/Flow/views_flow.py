from rest_framework.generics import GenericAPIView, RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Flow.models_flow import Flow
from api.Channel.models_channel import Channle
from api.Flow.serializers_flow import SerializerFlows


class AddListFlows(GenericAPIView):
    
    permission_classes = [IsAuthenticated]
    def post(self, request, channel_id):
        channel = get_object_or_404(Channle, channle_id=channel_id)
        flow = request.data['flow']
        flow_name = request.data['flow_name']
        flow_ = Flow.objects.create(account=channel.account_id, flow=flow, flow_name=flow_name)
        channel.flows.add(flow_)
        channel.save()

        return Response(status=status.HTTP_200_OK)
    
    def get(self, request, channel_id):
        channel = get_object_or_404(Channle, channle_id=channel_id)
        flows = channel.flows.all()
        serializer = SerializerFlows(flows, many=True, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)


class SetDefaultFlow(GenericAPIView):

    permission_classes = [IsAuthenticated]
    def post(self, request, channel_id):
        data = request.data
        try:
            channel = Channle.objects.filter(channle_id=channel_id).first()
            if not channel:
                return Response({'error':'No Channle found'}, status=status.HTTP_200_OK)
            flows = channel.flows.all()
        except:
            return Response({"error":"Channel matching query dose not exist"})
        for flow in flows:
            if str(flow.id) == data['flow_id']:
                
                flow.is_default = request.GET['is_default']
                flow.save()
            else:
                flow.is_default = 'False'
                flow.save()

        return Response(status=status.HTTP_200_OK)


class UpdateFlowView(GenericAPIView):
    def put(self, request, pk):
        data = request.data
        flow = get_object_or_404(Flow, id=pk)
        flow.flow_name = data['flow_name']
        flow.flow = data['flow']
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
