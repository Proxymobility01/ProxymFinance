# authentication/models.py

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'email est obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)  # Important: specify the database
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class Employe(AbstractBaseUser, PermissionsMixin):
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=255, unique=True)
    # Remove password field - AbstractBaseUser handles this
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Required fields for Django Auth
    last_login = models.DateTimeField(_('last login'), blank=True, null=True)
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom', 'prenom']

    class Meta:
        db_table = 'employes'

        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')
        # Remove the constraint - BigAutoField primary key is already unique

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})"

    def get_full_name(self):
        return f"{self.prenom} {self.nom}"

    def get_short_name(self):
        return self.prenom


class RoleFinance(models.Model):
    """
    Modèle pour les rôles financiers.
    Correspond à la table 'role_finance' dans la base de données.
    """
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'role_finance'


    def __str__(self):
        return self.title


class EmployeRoleFinance(models.Model):
    """
    Table de liaison entre employés et rôles financiers.
    Correspond à la table 'employe_role_finance' dans la base de données.
    """

    employe = models.ForeignKey(Employe, on_delete=models.CASCADE)
    role_finance = models.ForeignKey(RoleFinance, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'employe_role_finance'
        unique_together = ['employe', 'role_finance']  # Prevent duplicate assignments


# Modèles pour les autres types d'utilisateurs du système (basés sur vos tables existantes)

class Agence(models.Model):
    """
    Modèle pour les agences (stations).
    Correspond à la table 'agences' dans la base de données existante.
    """

    agence_unique_id = models.CharField(max_length=255, unique=True)
    nom_agence = models.CharField(max_length=255)
    nom_proprietaire = models.CharField(max_length=255)
    ville = models.CharField(max_length=255)
    quartier = models.CharField(max_length=255, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)

    telephone = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
    logo = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'agences'


    def __str__(self):
        return self.nom_agence


class UserAgence(models.Model):
    """
    Modèle pour les utilisateurs d'agence.
    Correspond à la table 'users_agences' dans la base de données existante.
    """

    user_agence_unique_id = models.CharField(max_length=255, unique=True)
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    ville = models.CharField(max_length=255)
    quartier = models.CharField(max_length=255)

    photo = models.CharField(max_length=255, null=True, blank=True)
    id_role_entite = models.BigIntegerField()  # Lien vers role_entites
    id_agence = models.ForeignKey(Agence, on_delete=models.CASCADE, db_column='id_agence')
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'users_agences'


    def __str__(self):
        return f"{self.prenom} {self.nom}"









