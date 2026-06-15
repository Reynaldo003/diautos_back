from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=200)

    class Meta:
        db_table = "roles"
        managed = True

    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    def create_user(self, usuario, correo, nombre, contrasena=None, **extra_fields):
        if not correo:
            raise ValueError("El usuario debe tener un correo electrónico.")
        if not usuario:
            raise ValueError("El nombre de usuario es obligatorio.")

        correo = self.normalize_email(correo)
        user = self.model(
            usuario=usuario,
            correo=correo,
            nombre=nombre,
            **extra_fields,
        )
        user.set_password(contrasena)
        user.save(using=self._db)
        return user

    def create_superuser(self, usuario, correo, nombre, contrasena=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        rol_admin, _ = Rol.objects.get_or_create(
            nombre="Administrador",
            defaults={"descripcion": "Acceso total al sistema"},
        )
        extra_fields.setdefault("rol", rol_admin)
        extra_fields.setdefault("agencia", "Matriz / Corporativo")

        return self.create_user(usuario, correo, nombre, contrasena, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=70, blank=True, null=True)
    usuario = models.CharField(max_length=10, unique=True)
    correo = models.EmailField(max_length=255, unique=True)
    rol = models.ForeignKey(Rol, db_column="rol", on_delete=models.PROTECT)
    agencia = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "usuario"
    REQUIRED_FIELDS = ["correo", "nombre"]

    objects = UsuarioManager()

    class Meta:
        db_table = "usuarios"
        managed = True

    @property
    def contrasena(self):
        return self.password

    @contrasena.setter
    def contrasena(self, value):
        self.set_password(value)

    def __str__(self):
        return f"{self.nombre} {self.apellidos or ''}".strip()