# clientes/models.py
from django.db import models
from django.core.exceptions import ValidationError

def normaliza_tel_mx(raw: str) -> str:
    digits = "".join(c for c in str(raw or "") if c.isdigit())
    if not digits:
        return ""
    if len(digits) == 10:
        return "52" + digits
    if len(digits) == 12 and digits.startswith("52"):
        return digits
    return ""

class ClienteComercial(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=200, blank=True, default="")
    telefono = models.CharField(max_length=32, db_index=True, unique=True)
    correo = models.EmailField(blank=True, default="")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clientes_comerciales"
        managed = True

    def save(self, *args, **kwargs):
        self.telefono = normaliza_tel_mx(self.telefono)
        if not self.telefono:
            raise ValidationError({"telefono": "Teléfono inválido. Debe tener 10 dígitos."})
        super().save(*args, **kwargs)

    def __str__(self):
        base = (self.nombre or "").strip() or "Cliente"
        return f"{base} ({self.telefono})".strip()