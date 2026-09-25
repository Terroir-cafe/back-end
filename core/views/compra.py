from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import Compra
from core.serializers import CompraCreateUpdateSerializer, CompraListSerializer, CompraSerializer


class CompraViewSet(ModelViewSet):
    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser:
            return Compra.objects.all()
        if usuario.groups.filter(name='administradores'):
            return Compra.objects.all()
        return Compra.objects.filter(usuario=usuario)

    def get_serializer_class(self):
        if self.action == 'list':
            return CompraListSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return CompraCreateUpdateSerializer
        return CompraSerializer

    @extend_schema(
        request=None,
        responses={200: None},
        description='Gera um relatório de vendas do mês atual.',
        summary='Relatório de vendas do mês',
    )
    @action(detail=False, methods=['get'])
    def relatorio_vendas_mes(self, request):
        agora = timezone.now()
        inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        compras = Compra.objects.filter(status=Compra.StatusCompra.FINALIZADO, data__gte=inicio_mes)

        total_vendas = sum(compra.total for compra in compras)
        quantidade_vendas = compras.count()

        return Response(
            {
                'status': 'Relatório de vendas deste mês',
                'total_vendas': total_vendas,
                'quantidade_vendas': quantidade_vendas,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=None,
        responses={200: None, 400: None},
        description='Finaliza a compra, atualizando o estoque dos produtos.',
        summary='Finalizar compra',
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def finalizar(self, request, pk=None):
        compra = self.get_object()

        # Verifica se a compra já foi finalizada
        if compra.status == Compra.StatusCompra.FINALIZADO:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'status': 'Compra já finalizada'})

        for item in compra.itens.all():
            # Valida se o estoque é suficiente para cada produto
            if item.quantidade > item.produto.quantidade:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={
                        'status': 'Quantidade insuficiente',
                        'produto': item.produto.nome,
                        'quantidade_disponivel': item.produto.quantidade,
                    },
                )

            # Atualiza o estoque dos produtos
            item.produto.quantidade -= item.quantidade
            item.produto.save()

        # Finaliza a compra: atualiza status
        compra.status = Compra.StatusCompra.FINALIZADO
        compra.save()

        return Response(status=status.HTTP_200_OK, data={'status': 'Compra finalizada'})
