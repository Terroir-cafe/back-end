from django.db import models, transaction

from uploader.models import Image

from .categoria import Categoria
from .marca import Marca


class ProdutoQuerySet(models.QuerySet):
    @transaction.atomic
    def update(self, **kwargs):
        if 'preco' not in kwargs:
            return super().update(**kwargs)

        # guarda os ids e preços antes, porque o filtro pode depender do próprio preço
        antigos = dict(self.values_list('pk', 'preco'))
        linhas = super().update(**kwargs)

        # relê do banco, pois o novo valor pode ser uma expressão (ex: F('preco') * 1.1)
        novos = Produto.objects.filter(pk__in=antigos).values_list('pk', 'preco')
        HistoricoPreco.objects.bulk_create(
            [
                HistoricoPreco(produto_id=pk, preco=preco)
                for pk, preco in novos
                if antigos[pk] != preco
            ]
        )
        return linhas

    @transaction.atomic
    def bulk_update(self, objs, fields, *args, **kwargs):
        objs = list(objs)
        if 'preco' not in fields:
            return super().bulk_update(objs, fields, *args, **kwargs)

        antigos = dict(
            Produto.objects.filter(pk__in=[o.pk for o in objs]).values_list('pk', 'preco')
        )
        linhas = super().bulk_update(objs, fields, *args, **kwargs)
        HistoricoPreco.objects.bulk_create(
            [
                HistoricoPreco(produto_id=o.pk, preco=o.preco)
                for o in objs
                if antigos.get(o.pk) != o.preco
            ]
        )
        return linhas

    @transaction.atomic
    def bulk_create(self, objs, *args, **kwargs):
        objs = super().bulk_create(objs, *args, **kwargs)
        HistoricoPreco.objects.bulk_create(
            [HistoricoPreco(produto_id=o.pk, preco=o.preco) for o in objs if o.pk]
        )
        return objs


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name='produtos', null=True, blank=True
    )
    marca = models.ForeignKey(
        Marca, on_delete=models.PROTECT, related_name='produtos', null=True, blank=True
    )
    quantidade = models.PositiveIntegerField(default=0)
    capa = models.ForeignKey(
        Image,
        related_name='+',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    objects = ProdutoQuerySet.as_manager()

    def __str__(self):
        return f'{self.nome} - {self.categoria} - {self.preco} - {self.marca} - {self.quantidade}'

    @transaction.atomic
    def save(self, *args, **kwargs):
        preco_antigo = None
        if self.pk:
            preco_antigo = (
                Produto.objects.filter(pk=self.pk).values_list('preco', flat=True).first()
            )

        super().save(*args, **kwargs)

        # grava no histórico na criação e sempre que o preço mudar
        if preco_antigo is None or preco_antigo != self.preco:
            self.historico_precos.create(preco=self.preco)


class HistoricoPreco(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='historico_precos')
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']

    def __str__(self):
        return f'{self.produto.nome} - R$ {self.preco} ({self.data:%d/%m/%Y})'