from django.db import models

from uploader.models import Image

from .categoria import Categoria
from .marca import Marca


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='produtos', null=True, blank=True)
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name='produtos', null=True, blank=True)
    quantidade = models.PositiveIntegerField(default=0)
    capa = models.ForeignKey(
        Image,
        related_name='+',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return f'{self.nome} - {self.categoria.nome} - {self.preco} - {self.marca} - {self.quantidade}'
