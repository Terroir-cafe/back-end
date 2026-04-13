from django.db import models

from .produto import Produto


class Estoque(models.Model):
    quantidade = models.IntegerField()
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f'{self.produto.nome} - {self.quantidade}'
