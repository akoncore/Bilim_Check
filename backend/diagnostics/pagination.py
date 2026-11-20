from django.core.paginator import Paginator
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param


class DiagnosticPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.size = self.get_page_size(request)
        try:
            self.number = int(request.query_params.get(self.page_query_param, 1))
        except ValueError as error:
            raise ValidationError({"page": "Бет нөмірі бүтін сан болуы керек."}) from error
        if not 1 <= self.number <= 1_000_000:
            raise ValidationError({"page": "Бет нөмірі 1–1000000 аралығында болуы керек."})
        paginator = Paginator(queryset, self.size)
        self.total, self.pages = paginator.count, paginator.num_pages
        if self.number > self.pages:
            return []
        return list(paginator.page(self.number))

    def link(self, number):
        return replace_query_param(self.request.build_absolute_uri(), self.page_query_param, number)

    def get_paginated_response(self, data):
        return Response({
            "items": data,
            "page": self.number,
            "page_size": self.size,
            "total": self.total,
            "next": self.link(self.number + 1) if self.number < self.pages else None,
            "previous": self.link(self.number - 1) if 1 < self.number <= self.pages + 1 else None,
        })
