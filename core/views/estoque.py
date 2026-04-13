from rest_framework.viewsets import ModelViewSet

from core.models import Estoque
from core.serializers import EstoqueSerializer


class EstoqueViewSet(ModelViewSet):
    queryset = Estoque.objects.all()
    serializer_class = EstoqueSerializer
