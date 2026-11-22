from django.db import models, transaction

from uploader.models import Image

from .categoria import Categoria
from .marca import Marca
from .notificacao import Notificacao


class ProdutoQuerySet(models.QuerySet):
    def com_queda_de_preco(self):
        ultimo_preco_distinto = (
            HistoricoPreco.objects.filter(produto_id=models.OuterRef('pk'))
            .exclude(preco=models.OuterRef('preco'))
            .order_by('-data', '-pk')
            .values('preco')[:1]
        )
        return self.alias(preco_comparacao=models.Subquery(ultimo_preco_distinto)).annotate(
            preco_anterior=models.Case(
                models.When(preco_comparacao__gt=models.F('preco'), then=models.F('preco_comparacao')),
            )
        )

    @transaction.atomic
    def update(self, **kwargs):
        if 'preco' not in kwargs:
            return super().update(**kwargs)

        # guarda os ids e preços antes, porque o filtro pode depender do próprio preço
        antigos = dict(self.order_by('pk').select_for_update().values_list('pk', 'preco'))
        linhas = super().update(**kwargs)

        # bulk_update também passa por este método, usando uma expressão CASE.
        for produto in self.model.objects.filter(pk__in=antigos):
            produto.registrar_preco(antigos[produto.pk])
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
        campos = kwargs.get('update_fields')
        if campos is not None and 'preco' not in campos:
            return super().save(*args, **kwargs)

        anterior = None
        if self.pk:
            anterior = Produto.objects.select_for_update().filter(pk=self.pk).values_list('preco', flat=True).first()

        super().save(*args, **kwargs)
        # Lê o preço efetivamente salvo, inclusive com update_fields ou expressões.
        Produto.objects.get(pk=self.pk).registrar_preco(anterior)

    def registrar_preco(self, anterior):
        if anterior == self.preco:
            return
        if anterior is not None and not self.historico_precos.exists():
            self.historico_precos.create(preco=anterior)
        self.historico_precos.create(preco=self.preco)
        if anterior is None or anterior <= self.preco:
            return

        antigo = f'{anterior:.2f}'.replace('.', ',')
        atual = f'{self.preco:.2f}'.replace('.', ',')
        Notificacao.objects.registrar(
            Notificacao(
                usuario_id=usuario_id,
                tipo=Notificacao.Tipo.PRECO,
                produto=self,
                mensagem=f'O preço de {self.nome} caiu de R$ {antigo} para R$ {atual}.',
            )
            for usuario_id in self.favoritos.values_list('pk', flat=True)
        )


class HistoricoPreco(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='historico_precos')
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']

    def __str__(self):
        return f'{self.produto.nome} - R$ {self.preco} ({self.data:%d/%m/%Y})'
