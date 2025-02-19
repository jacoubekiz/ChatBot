from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
class CustomPaginatins(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'size_page'
    max_page_size = 600

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "next": self.get_next_link()[28:],
            "previous": self.get_previous_link()[28:],
            "results": data
        })