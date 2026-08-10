from rest_framework.serializers import ModelSerializer, SlugRelatedField

from core.models import Categoria
from uploader.models import Image
from uploader.serializers import ImageSerializer


class CategoriaSerializer(ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class LivroRetrieveSerializer(ModelSerializer):
    capa = ImageSerializer(required=False)

    class Meta:
        model = Categoria
        fields = '__all__'
        depth = 1


class CategoriaSerializer(ModelSerializer):
    capa_attachment_key = SlugRelatedField(
        source='capa',
        queryset=Image.objects.all(),
        slug_field='attachment_key',
        required=False,
        write_only=True,
    )
    capa = ImageSerializer(required=False, read_only=True)

    class Meta:
        model = Categoria
        fields = '__all__'
