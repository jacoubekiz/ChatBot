from rest_framework.pagination import PageNumberPagination

class CustomPaginatins(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'size_page'
    max_page_size = 600