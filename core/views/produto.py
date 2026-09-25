from django.db.models import Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import Produto, Compra
from core.serializers import (
    ProdutoAlterarPrecoSerializer,
    ProdutoListSerializer,
    ProdutoRetrieveSerializer,
    ProdutoSerializer,
    ProdutoMaisVendidoSerializer,
)


class ProdutoViewSet(ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['categoria__nome', 'marca__nome', 'preco', 'quantidade']
    ordering_fields = ['preco', 'quantidade']
    search_fields = ['nome', 'descricao']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProdutoListSerializer
        elif self.action == 'retrieve':
            return ProdutoRetrieveSerializer
        return ProdutoSerializer

    @extend_schema(
        request=ProdutoAlterarPrecoSerializer,
        responses={200: None},
        description='Altera o preço de um produto específico.',
        summary='Alterar preço do produto',
    )
    @action(detail=True, methods=['patch'])
    def alterar_preco(self, request, pk=None):
        produto = self.get_object()

        serializer = ProdutoAlterarPrecoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        produto.preco = serializer.validated_data['preco']
        produto.save()

        return Response(
            {
                'detail': f'Preço do produto "{produto.nome}" atualizado para {produto.preco}.',
            },
            status=status.HTTP_200_OK,
        )
    @action(detail=False, methods=['get'])
    def mais_vendidos(self, request):
        produtos = Produto.objects.annotate(
            total_vendidos=Sum(
                'itens_compra__quantidade',
                filter=Q(itens_compra__compra__status=Compra.StatusCompra.FINALIZADO)
            )
        ).filter(total_vendidos__gt=10).order_by('-total_vendidos')

        serializer = ProdutoMaisVendidoSerializer(produtos, many=True)

        if not serializer.data:
            return Response(
                {"detail": "Nenhum produto excedeu 10 vendas."},
                status=status.HTTP_200_OK
            )

        return Response(serializer.data, status=status.HTTP_200_OK)
