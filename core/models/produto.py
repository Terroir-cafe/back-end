from django.db import models

from .categoria import Categoria


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='produtos', null=True, blank=True)

    def __str__(self):
        return f'{self.nome} - {self.categoria.nome} - {self.preco} - {self.descricao}'
