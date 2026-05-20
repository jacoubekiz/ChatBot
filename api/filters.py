import django_filters
from django.db.models import Count, Q
from .models import Contact, Conversation, Tag

class ContactFilter(django_filters.FilterSet):
    # Filter by single tag name
    tag_name = django_filters.CharFilter(
        method='filter_by_tag_name',
        label='Filter contacts by conversation tag name'
    )
    
    # Filter by multiple tag names (OR logic)
    tag_names = django_filters.BaseInFilter(
        method='filter_by_tag_names',
        label='Filter by multiple tag names (comma-separated)'
    )
    
    # Filter by tag name with partial match
    tag_name_contains = django_filters.CharFilter(
        method='filter_by_tag_name_contains',
        label='Tag name contains'
    )
    
    # Filter contacts that have conversations with ALL specified tags
    required_tags = django_filters.BaseInFilter(
        method='filter_by_required_tags',
        label='Contacts must have conversations with ALL these tags'
    )
    
    # Filter by tag count on conversations
    min_conversation_tags = django_filters.NumberFilter(
        method='filter_by_min_conversation_tags',
        label='Minimum number of tags on conversations'
    )
    
    def filter_by_tag_name(self, queryset, name, value):
        """
        Filter contacts that have at least one conversation with the given tag
        """
        if value:
            queryset = queryset.filter(
                conversation__tags__name=value
            ).distinct()
        return queryset
    
    def filter_by_tag_names(self, queryset, name, value):
        """
        Filter contacts that have conversations with any of the given tags
        Example: ?tag_names=urgent,important
        """
        if value:
            queryset = queryset.filter(
                conversation__tags__name__in=value
            ).distinct()
        return queryset
    
    def filter_by_tag_name_contains(self, queryset, name, value):
        """
        Filter by partial tag name match
        Example: ?tag_name_contains=urg (matches 'urgent', 'urgent_care')
        """
        if value:
            queryset = queryset.filter(
                conversation__tags__name__icontains=value
            ).distinct()
        return queryset
    
    def filter_by_required_tags(self, queryset, name, value):
        """
        Filter contacts that have conversations with ALL specified tags
        Example: ?required_tags=urgent,important
        """
        if value:
            for tag_name in value:
                queryset = queryset.filter(
                    conversation__tags__name=tag_name
                )
        return queryset.distinct()
    
    def filter_by_min_conversation_tags(self, queryset, name, value):
        """
        Filter contacts that have conversations with at least N distinct tags
        """
        if value:
            queryset = queryset.annotate(
                conversation_tag_count=Count('conversation__tags', distinct=True)
            ).filter(conversation_tag_count__gte=value)
        return queryset
    
    class Meta:
        model = Contact
        fields = ['tag_name', 'tag_names', 'tag_name_contains', 'required_tags', 'min_conversation_tags']

            

class ConversationFilter(django_filters.FilterSet):

    class Meta:
        model = Conversation
        fields = {
            'contact_id__name': ['icontains'],
            'contact_id__phone_number': ['icontains'],
            'created_at': ['date__gte', 'date__lte'],
        }