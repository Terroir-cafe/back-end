from rest_framework.viewsets import ModelViewSet

from core.models import Produto
from core.serializers import ProdutoListSerializer, ProdutoRetrieveSerializer, ProdutoSerializer


class ProdutoViewSet(ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return ProdutoListSerializer
        elif self.action == 'retrieve':
            return ProdutoRetrieveSerializer
        return ProdutoSerializer
