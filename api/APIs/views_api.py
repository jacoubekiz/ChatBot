from rest_framework.generics import (
    GenericAPIView, 
    UpdateAPIView, 
    DestroyAPIView, 
    ListCreateAPIView, 
    RetrieveUpdateDestroyAPIView, 
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Flow.models_flow import (
    Custome_attribute,
    Attribute
)
from api.APIs.models_api import (
    API, 
    Parameter, 
    Api_parameter, 
    Account
)
from api.APIs.serializers_api import (
    APISerializer, 
    APIParametersSerializer, 
    SerializerCustomeAttributes, 
    APILogSerializer, 
    ParameterSerializer, 
    SerializerAttributes
)

class ListCreateApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        account = get_object_or_404(Account, account_id=account_id)
        data = request.data

        # validate data not empty
        if not data:
            return Response(
                {'error':'No data provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        parameters = data.get('parameters', [])
        custome_attrs = data.get('custome_attrs', [])

        # Validate parameters is a list
        if not isinstance(parameters, list):
            return Response(
                {'error':'Parameters must be a list'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        # Validate custome attributes is a list
        if not isinstance(custome_attrs, list):
            return Response(
                {'error':'Custome attributes must be a list'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = APISerializer(
            data=data, 
            context={
                'account':account, 
                'parameters':parameters,
                'custome_attrs': custome_attrs
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'API created successfully'}, status=status.HTTP_201_CREATED)
        return Response({'error':serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, account_id):
        account = get_object_or_404(Account, account_id=account_id)
        api_objects = API.objects.filter(account_id=account).prefetch_related('api_parameter_set')
        if not api_objects.exists():
            return Response(
                {'message': 'No APIs found for this account'}, 
                status=status.HTTP_200_OK
            )
        
        result = []
        for api_object in api_objects:
            api_parameters = api_object.api_parameter_set.all()
            serializer_api_param = APIParametersSerializer(api_parameters, many=True) 
            serializer = APISerializer(api_object)

            data_dict = serializer.data
            data_dict['parameters'] = serializer_api_param.data

            result.append(data_dict)
        return Response(result, status=status.HTTP_200_OK)


class GetApiView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = APISerializer
    lookup_field = 'api_id'

    def get(self, request, api_id):
        api_object = API.objects.filter(api_id=api_id).first()
        if not api_object:
            return Response({'error':'No API found'}, status=status.HTTP_200_OK)
        api_parameters = Api_parameter.objects.filter(api=api_object)
        serializer_api_param = APIParametersSerializer(api_parameters, many=True)
        serializer = APISerializer(api_object)
        data = serializer.data
        data_dict = dict(data)
        custome_attributes = Custome_attribute.objects.filter(api=api_object)
        seria = SerializerCustomeAttributes(custome_attributes, many=True)
        data_dict['parameters'] = serializer_api_param.data
        data_dict['custome_attrs'] = seria.data

        return Response(data_dict, status=status.HTTP_200_OK)
            

class UpdateApiview(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = APISerializer
    queryset = API.objects.all()
    lookup_field = 'api_id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['parameters'] = self.request.data.get('parameters', [])
        context['custome_attrs'] = self.request.data.get('custome_attrs', [])
        return context
    

class SaveResponse(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, api_id):
        response = request.data['response']
        api = get_object_or_404(API, api_id=api_id)
        api.response = response
        api.save()
        return Response(status=status.HTTP_200_OK)


class DeleteAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = APISerializer
    queryset = API.objects.all()
    lookup_field = 'api_id'


class APILogVeiw(GenericAPIView):
    serializer_class = APILogSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, api_id):
        api = API.objects.filter(api_id=api_id).first()
        if not api:
            return Response({'error':'No API found'}, status=status.HTTP_200_OK)
        api_log = APILog.objects.filter(api=api)
        apis_logs = []
        for api_log_ in api_log:
            data = {
                "id":api_log_.apilog_id,
                "status": api_log_.status_request,
                "message":"",
                "created_at":api_log_.created_at,
                "request": {
                    "url": api_log_.api.endpoint,
                    "method":api_log_.api.method,
                    "data":{
                        api_log_.api.body if api_log_.api.body else "",
                    },
                },
                "response": {
                    "status": api_log_.status_request,
                    "message":"",
                    "payload": {
                        str(api_log_.response) if api_log_.response else ""
                    }
                }
            }
            apis_logs.append(data)
        return Response(apis_logs, status=status.HTTP_200_OK)


class DeleteParameterAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ParameterSerializer
    queryset = Parameter.objects.all()
    lookup_field = 'parameter_id'


class ListCreateAttributeView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        account = Account.objects.filter(account_id=account_id).first()
        if not account:
            return Response({'error':'No account found'}, status=status.HTTP_200_OK)
        data = request.data
        serializer = SerializerAttributes(
            data=data, 
            context={
                'account':account
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)
    
    def get(self, request, account_id):
        account = Account.objects.filter(account_id=account_id).first()
        if not account:
            return Response({'error':'No account found'}, status=status.HTTP_200_OK)
        attributes = Attribute.objects.filter(account_id=account)
        if not attributes:
            return Response({'error':'No attributes found'}, status=status.HTTP_200_OK)
        serializer = SerializerAttributes(attributes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class RetAupDelAttributeView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SerializerAttributes
    lookup_field = 'id'

    def get_queryset(self):
        attribute_id = self.kwargs['id']
        account = self.kwargs['account_id']
        return Attribute.objects.filter(account=account, id=attribute_id)
    
    def perform_update(self, serializer):
        account_id = get_object_or_404(Account, account_id=self.kwargs['account_id'])
        serializer.save(account=account_id)
