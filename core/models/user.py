"""
Database models.
"""

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from uploader.models import Image

from .produto import Produto


class UserManager(BaseUserManager):
    """Manager for users."""

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).strip().lower()

    def get_by_natural_key(self, email):
        return super().get_by_natural_key(self.normalize_email(email))

    async def aget_by_natural_key(self, email):
        return await super().aget_by_natural_key(self.normalize_email(email))

    def create_user(self, email, password=None, **extra_fields):
        """Create, save and return a new user."""
        email = self.normalize_email(email)
        if not email:
            raise ValueError('Users must have an email address.')

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        """Create, save and return a new superuser."""
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """User model in the system."""

    email = models.EmailField(max_length=255, unique=True, verbose_name=_('email'), help_text=_('Email'))
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('name'), help_text=_('Username'))
    is_active = models.BooleanField(
        default=True, verbose_name=_('Usuário está ativo'), help_text=_('Indica que este usuário está ativo.')
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_('Usuário é da equipe'),
        help_text=_('Indica que este usuário pode acessar o Admin.'),
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        """Meta options for the model."""

        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        constraints = [models.UniqueConstraint(Lower('email'), name='usuario_email_unico_sem_maiusculas')]

    foto = models.ForeignKey(
        Image,
        related_name='user_foto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )
    favoritos = models.ManyToManyField(Produto, related_name='favoritos', blank=True)


    def save(self, *args, **kwargs):
        campos = kwargs.get('update_fields')
        if campos is None or 'email' in campos:
            self.email = self.__class__.objects.normalize_email(self.email)
        return super().save(*args, **kwargs)
