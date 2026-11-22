from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.serializers import (
    CharField,
    EmailField,
    ModelSerializer,
    RegexField,
    Serializer,
    SlugRelatedField,
    ValidationError,
)
from rest_framework.validators import UniqueValidator

from core.models import Notificacao, User
from core.push import endpoint_permitido
from uploader.models import Image
from uploader.serializers import ImageSerializer


EMAIL_EM_USO = 'Já existe uma conta com este e-mail.'
GRUPO_COMPRADOR = 'Comprador'


class EmailNormalizadoField(EmailField):
    def __init__(self, **kwargs):
        super().__init__(
            max_length=User._meta.get_field('email').max_length,
            validators=[UniqueValidator(queryset=User.objects.all(), lookup='iexact', message=EMAIL_EM_USO)],
            **kwargs,
        )

    def to_internal_value(self, data):
        return User.objects.normalize_email(super().to_internal_value(data))


class UserSerializer(ModelSerializer):
    email = EmailNormalizadoField()
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
    email = EmailNormalizadoField()
    password = CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'password']

    def validate(self, attrs):
        usuario = User(email=attrs['email'], name=attrs.get('name'))
        try:
            validate_password(attrs['password'], user=usuario)
        except DjangoValidationError as exc:
            raise ValidationError({'password': exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                usuario = User.objects.create_user(**validated_data)
                grupo, _ = Group.objects.get_or_create(name=GRUPO_COMPRADOR)
                usuario.groups.add(grupo)
        except IntegrityError as exc:
            if User.objects.filter(email=validated_data['email']).exists():
                raise ValidationError({'email': [EMAIL_EM_USO]}) from exc
            raise
        return usuario


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
