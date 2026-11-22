from rest_framework.serializers import CharField, ModelSerializer, RegexField, Serializer, SlugRelatedField, ValidationError

from core.models import Notificacao, User
from core.push import endpoint_permitido
from uploader.models import Image
from uploader.serializers import ImageSerializer


class UserSerializer(ModelSerializer):
    foto_attachment_key = SlugRelatedField(
        source='foto',
        queryset=Image.objects.all(),
        slug_field='attachment_key',
        required=False,
        write_only=True,
    )
    foto = ImageSerializer(required=False, read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'name',
            'foto',
            'foto_attachment_key',
            'is_active',
            'is_staff',
            'is_superuser',
            'last_login',
            'groups',
            'favoritos',
        )
        read_only_fields = ('is_active', 'is_staff', 'is_superuser', 'last_login')
        depth = 1


class UserRegistrationSerializer(ModelSerializer):
    password = CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class FavoritoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('favoritos',)


class NotificacaoSerializer(ModelSerializer):
    class Meta:
        model = Notificacao
        fields = ('id', 'tipo', 'mensagem', 'produto', 'criada_em', 'lida_em')


class ChavesPushSerializer(Serializer):
    p256dh = RegexField(r'^[A-Za-z0-9_-]{87}=?$', trim_whitespace=False)
    auth = RegexField(r'^[A-Za-z0-9_-]{22}(?:==)?$', trim_whitespace=False)


class DispositivoPushSerializer(Serializer):
    endpoint = CharField(max_length=2048, trim_whitespace=False)
    keys = ChavesPushSerializer()

    def validate_endpoint(self, endpoint):
        if not endpoint_permitido(endpoint):
            raise ValidationError('Serviço de notificações incompatível.')
        return endpoint
