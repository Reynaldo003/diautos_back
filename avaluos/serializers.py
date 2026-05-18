import json
import mimetypes
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import serializers

from clientes.models import ClienteComercial, normaliza_tel_mx
from .models import AvaluoUsado, AvaluoUsadoEvidencia, ConceptoAvaluo


class ClienteComercialMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteComercial
        fields = ("id_cliente", "nombre", "telefono", "correo")


class AvaluoUsadoEvidenciaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    costo = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = AvaluoUsadoEvidencia
        fields = (
            "id",
            "nombre",
            "tipo",
            "categoria_concepto",
            "costo",
            "descripcion",
            "archivo",
            "url",
            "creado",
        )
        read_only_fields = ("id", "tipo", "archivo", "url", "creado")

    def get_url(self, obj):
        if not obj.archivo:
            return ""

        try:
            url = obj.archivo.url
        except Exception:
            return ""

        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ConceptoAvaluoSerializer(serializers.ModelSerializer):
    costo = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = ConceptoAvaluo
        fields = ("id", "descripcion", "tipo_concepto", "costo")
        read_only_fields = ("id",)


class BaseClienteComercialSerializer(serializers.ModelSerializer):
    cliente = ClienteComercialMiniSerializer(read_only=True)

    cliente_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    nombre = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")
    telefono = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")
    correo = serializers.EmailField(write_only=True, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        attrs = super().validate(attrs)

        telefono = attrs.get("telefono")
        cliente_id = attrs.get("cliente_id")

        if self.instance is None:
            if not cliente_id and not str(telefono or "").strip():
                raise serializers.ValidationError({
                    "telefono": "El teléfono es requerido para crear el registro."
                })

        if telefono is not None and str(telefono).strip():
            telefono_normalizado = normaliza_tel_mx(telefono)
            if not telefono_normalizado:
                raise serializers.ValidationError({
                    "telefono": "Teléfono inválido. Debe tener 10 dígitos o 52 + 10 dígitos."
                })

            attrs["telefono"] = telefono_normalizado

        return attrs

    def _resolver_cliente(self, validated_data):
        cliente_id = validated_data.pop("cliente_id", None)
        nombre = validated_data.pop("nombre", "")
        telefono = validated_data.pop("telefono", "")
        correo = validated_data.pop("correo", "")

        if cliente_id:
            try:
                cliente = ClienteComercial.objects.get(pk=cliente_id)
            except ClienteComercial.DoesNotExist:
                raise serializers.ValidationError({
                    "cliente_id": "El cliente indicado no existe."
                })

            cambios = False

            if nombre is not None and str(nombre).strip() != (cliente.nombre or ""):
                cliente.nombre = nombre
                cambios = True

            if correo is not None and str(correo).strip() != (cliente.correo or ""):
                cliente.correo = correo
                cambios = True

            if telefono:
                telefono_normalizado = normaliza_tel_mx(telefono)
                if not telefono_normalizado:
                    raise serializers.ValidationError({
                        "telefono": "Teléfono inválido."
                    })

                if telefono_normalizado != cliente.telefono:
                    existe = (
                        ClienteComercial.objects
                        .filter(telefono=telefono_normalizado)
                        .exclude(pk=cliente.pk)
                        .exists()
                    )

                    if existe:
                        raise serializers.ValidationError({
                            "telefono": "Ya existe otro cliente con ese teléfono."
                        })

                    cliente.telefono = telefono_normalizado
                    cambios = True

            if cambios:
                cliente.save()

            return cliente

        telefono = normaliza_tel_mx(telefono)
        if not telefono:
            raise serializers.ValidationError({
                "telefono": "El teléfono es requerido."
            })

        cliente, _ = ClienteComercial.objects.get_or_create(
            telefono=telefono,
            defaults={
                "nombre": nombre or "",
                "correo": correo or "",
            },
        )

        cambios = False

        if nombre is not None and str(nombre).strip() and cliente.nombre != nombre:
            cliente.nombre = nombre
            cambios = True

        if correo is not None and cliente.correo != correo:
            cliente.correo = correo
            cambios = True

        if cambios:
            cliente.save()

        return cliente


class AvaluoUsadoSerializer(BaseClienteComercialSerializer):
    evidencias = AvaluoUsadoEvidenciaSerializer(many=True, read_only=True)
    conceptos = ConceptoAvaluoSerializer(many=True, read_only=True)

    conceptos_json = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        default="",
    )

    evidencias_metadata_json = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        default="",
    )

    evidencias_existentes_json = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        default="",
    )

    checklist_100_json = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        default="",
    )

    delete_evidencia_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = AvaluoUsado
        fields = (
            "id",
            "cliente",
            "cliente_id",
            "nombre",
            "telefono",
            "correo",

            "agencia",
            "fecha_avaluo",
            "fecha_finalizacion",
            "fecha_toma_cuenta",
            "agenda_valuacion",

            "asesor_ventas",
            "vendedor",
            "tipo_valuacion",
            "tipo_toma",

            "marca_auto",
            "modelo",
            "anio_modelo",
            "version",
            "serie",
            "placas",
            "kilometraje",
            "color",

            "precio_guia",
            "precio_compra_libro_azul",
            "precio_venta_libro_azul",
            "costo_reparacion",
            "costo_estimado",
            "costo_mecanica_total",
            "oferta_inicial",
            "oferta_final",

            "origen_valuacion",
            "descripcion",
            "observaciones",
            "comentarios",

            "ganador_subasta",
            "etapa_proceso",

            "checklist_100",
            "tecnico_finalizado",
            "fecha_tecnico_finalizado",
            "valuacion_terminada",
            "fecha_valuacion_terminada",

            "evidencias",
            "conceptos",

            "conceptos_json",
            "evidencias_metadata_json",
            "evidencias_existentes_json",
            "checklist_100_json",
            "delete_evidencia_ids",

            "creado",
            "actualizado",
        )

        read_only_fields = (
            "id",
            "cliente",
            "costo_reparacion",
            "evidencias",
            "conceptos",
            "tecnico_finalizado",
            "fecha_tecnico_finalizado",
            "valuacion_terminada",
            "fecha_valuacion_terminada",
            "creado",
            "actualizado",
        )

    def _parse_decimal(self, valor):
        texto = str(valor or "").strip()

        if not texto:
            return Decimal("0.00")

        texto = texto.replace("$", "").replace(",", "").replace(" ", "")

        try:
            return Decimal(texto).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise serializers.ValidationError({
                "monto": f"Monto inválido: '{valor}'."
            })

    def _parse_json(self, raw, campo, default):
        if raw in (None, "", []):
            return default

        if isinstance(raw, (dict, list)):
            return raw

        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                raise serializers.ValidationError({
                    campo: f"El formato de {campo} no es válido."
                })

        raise serializers.ValidationError({
            campo: f"El campo {campo} debe ser JSON válido."
        })

    def _normalizar_tipo_concepto(self, valor):
        tipo = str(valor or "").strip().lower()

        permitidos = {
            ConceptoAvaluo.TIPO_MECANICO,
            ConceptoAvaluo.TIPO_ESTETICO,
            ConceptoAvaluo.TIPO_HYP,
        }

        if tipo not in permitidos:
            raise serializers.ValidationError({
                "conceptos_json": "El tipo de concepto debe ser mecanico, estetico o hyp."
            })

        return tipo

    def _normalizar_conceptos(self, raw_conceptos):
        raw_conceptos = self._parse_json(raw_conceptos, "conceptos_json", [])

        if not isinstance(raw_conceptos, list):
            raise serializers.ValidationError({
                "conceptos_json": "Los conceptos deben enviarse como una lista."
            })

        conceptos = []

        for item in raw_conceptos:
            if not isinstance(item, dict):
                raise serializers.ValidationError({
                    "conceptos_json": "Cada concepto debe ser un objeto."
                })

            descripcion = str(item.get("descripcion") or "").strip()
            tipo_concepto = self._normalizar_tipo_concepto(
                item.get("tipo_concepto") or ConceptoAvaluo.TIPO_MECANICO
            )

            costo = self._parse_decimal(item.get("costo"))

            if tipo_concepto == ConceptoAvaluo.TIPO_MECANICO:
                costo = Decimal("0.00")

            if not descripcion and costo == Decimal("0.00"):
                continue

            if not descripcion:
                raise serializers.ValidationError({
                    "conceptos_json": "Cada concepto debe tener descripción."
                })

            conceptos.append({
                "descripcion": descripcion,
                "tipo_concepto": tipo_concepto,
                "costo": costo,
            })

        return conceptos

    def _normalizar_categoria_evidencia(self, valor):
        categoria = str(valor or "").strip().lower()

        permitidos = {
            AvaluoUsadoEvidencia.CATEGORIA_ESTETICO,
            AvaluoUsadoEvidencia.CATEGORIA_MECANICO,
            AvaluoUsadoEvidencia.CATEGORIA_HYP,
        }

        if categoria not in permitidos:
            raise serializers.ValidationError({
                "evidencias_metadata_json": "La categoría debe ser estetico, mecanico o hyp."
            })

        return categoria

    def _normalizar_evidencias_metadata(self, raw_metadata):
        raw_metadata = self._parse_json(raw_metadata, "evidencias_metadata_json", [])

        if not isinstance(raw_metadata, list):
            raise serializers.ValidationError({
                "evidencias_metadata_json": "La metadata de evidencias debe ser una lista."
            })

        metadata = []

        for item in raw_metadata:
            if not isinstance(item, dict):
                item = {}

            metadata.append({
                "categoria_concepto": self._normalizar_categoria_evidencia(
                    item.get("categoria_concepto") or AvaluoUsadoEvidencia.CATEGORIA_ESTETICO
                ),
                "costo": self._parse_decimal(item.get("costo")),
                "descripcion": str(item.get("descripcion") or "").strip(),
            })

        return metadata

    def _normalizar_evidencias_existentes(self, raw_data):
        raw_data = self._parse_json(raw_data, "evidencias_existentes_json", [])

        if not isinstance(raw_data, list):
            raise serializers.ValidationError({
                "evidencias_existentes_json": "Las evidencias existentes deben enviarse como una lista."
            })

        evidencias = []

        for item in raw_data:
            if not isinstance(item, dict):
                continue

            evidencia_id = item.get("id")

            if not evidencia_id:
                continue

            try:
                evidencia_id = int(evidencia_id)
            except ValueError:
                raise serializers.ValidationError({
                    "evidencias_existentes_json": "El id de evidencia debe ser entero."
                })

            evidencias.append({
                "id": evidencia_id,
                "categoria_concepto": self._normalizar_categoria_evidencia(
                    item.get("categoria_concepto") or AvaluoUsadoEvidencia.CATEGORIA_ESTETICO
                ),
                "costo": self._parse_decimal(item.get("costo")),
                "descripcion": str(item.get("descripcion") or "").strip(),
            })

        return evidencias

    def _normalizar_checklist(self, raw_checklist):
        raw_checklist = self._parse_json(raw_checklist, "checklist_100_json", {})

        if raw_checklist in (None, ""):
            return {}

        if not isinstance(raw_checklist, dict):
            raise serializers.ValidationError({
                "checklist_100_json": "El checklist debe ser un objeto JSON."
            })

        permitidos = {
            "",
            "inspeccion_realizada",
            "requiere_servicio",
            "servicio_realizado",
            "na",
            "si",
            "no",
        }

        limpio = {}

        for key, value in raw_checklist.items():
            numero = str(key).strip()
            estado = str(value or "").strip().lower()

            if not numero.isdigit():
                continue

            numero_int = int(numero)

            if numero_int < 1 or numero_int > 100:
                continue

            if estado not in permitidos:
                raise serializers.ValidationError({
                    "checklist_100_json": "Estado inválido en checklist."
                })

            if estado:
                limpio[str(numero_int)] = estado

        return limpio

    def _obtener_desde_request(self, attrs, nombre_campo):
        request = self.context.get("request")

        if request is not None and hasattr(request.data, "get") and nombre_campo in request.data:
            return request.data.get(nombre_campo)

        return attrs.get(nombre_campo, None)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        request = self.context.get("request")

        archivos = []
        if request is not None and hasattr(request.FILES, "getlist"):
            archivos = request.FILES.getlist("evidencias_nuevas")

        for archivo in archivos:
            if archivo.size > 50 * 1024 * 1024:
                raise serializers.ValidationError({
                    "evidencias_nuevas": f"El archivo '{archivo.name}' supera el límite de 50 MB."
                })

            content_type = getattr(archivo, "content_type", "") or ""
            if not content_type.startswith("image/"):
                raise serializers.ValidationError({
                    "evidencias_nuevas": "Por ahora las evidencias del avalúo deben ser imágenes."
                })

        delete_ids = attrs.get("delete_evidencia_ids", [])

        if request is not None and hasattr(request.data, "getlist"):
            raw_delete_ids = request.data.getlist("delete_evidencia_ids")
            if raw_delete_ids:
                delete_ids = raw_delete_ids

        delete_ids_limpios = []

        for valor in delete_ids or []:
            valor = str(valor).strip()

            if not valor:
                continue

            try:
                delete_ids_limpios.append(int(valor))
            except ValueError:
                raise serializers.ValidationError({
                    "delete_evidencia_ids": "Todos los IDs de evidencias a eliminar deben ser enteros."
                })

        raw_conceptos = self._obtener_desde_request(attrs, "conceptos_json")
        raw_metadata = self._obtener_desde_request(attrs, "evidencias_metadata_json")
        raw_existentes = self._obtener_desde_request(attrs, "evidencias_existentes_json")
        raw_checklist = self._obtener_desde_request(attrs, "checklist_100_json")

        attrs["_conceptos_recibidos"] = raw_conceptos is not None
        attrs["_conceptos"] = (
            self._normalizar_conceptos(raw_conceptos)
            if raw_conceptos is not None
            else []
        )

        attrs["_evidencias_metadata"] = self._normalizar_evidencias_metadata(raw_metadata)
        attrs["_evidencias_existentes"] = self._normalizar_evidencias_existentes(raw_existentes)
        attrs["_checklist_recibido"] = raw_checklist is not None
        attrs["_checklist_100"] = (
            self._normalizar_checklist(raw_checklist)
            if raw_checklist is not None
            else {}
        )

        attrs["_evidencias_nuevas"] = archivos
        attrs["_delete_evidencia_ids"] = delete_ids_limpios

        return attrs

    def _inferir_tipo_archivo(self, archivo):
        content_type = getattr(archivo, "content_type", "") or ""

        if not content_type:
            content_type = mimetypes.guess_type(getattr(archivo, "name", ""))[0] or ""

        if content_type.startswith("image/"):
            return AvaluoUsadoEvidencia.TIPO_IMAGEN

        if content_type.startswith("video/"):
            return AvaluoUsadoEvidencia.TIPO_VIDEO

        return AvaluoUsadoEvidencia.TIPO_ARCHIVO

    def _crear_evidencias(self, avaluo, archivos, metadata):
        for index, archivo in enumerate(archivos):
            meta = metadata[index] if index < len(metadata) else {}

            AvaluoUsadoEvidencia.objects.create(
                avaluo=avaluo,
                archivo=archivo,
                nombre=getattr(archivo, "name", "") or "archivo",
                tipo=self._inferir_tipo_archivo(archivo),
                categoria_concepto=meta.get(
                    "categoria_concepto",
                    AvaluoUsadoEvidencia.CATEGORIA_ESTETICO,
                ),
                costo=meta.get("costo", Decimal("0.00")),
                descripcion=meta.get("descripcion", ""),
            )

    def _actualizar_evidencias_existentes(self, avaluo, evidencias):
        for item in evidencias:
            AvaluoUsadoEvidencia.objects.filter(
                avaluo=avaluo,
                id=item["id"],
            ).update(
                categoria_concepto=item["categoria_concepto"],
                costo=item["costo"],
                descripcion=item["descripcion"],
            )

    def _guardar_conceptos(self, avaluo, conceptos):
        avaluo.conceptos.all().delete()

        for item in conceptos:
            ConceptoAvaluo.objects.create(
                avaluo=avaluo,
                descripcion=item["descripcion"],
                tipo_concepto=item["tipo_concepto"],
                costo=item["costo"],
            )

    def _recalcular_total_reparacion(self, avaluo):
        total = Decimal("0.00")

        total += avaluo.costo_mecanica_total or Decimal("0.00")

        for concepto in avaluo.conceptos.all():
            total += concepto.costo or Decimal("0.00")

        for evidencia in avaluo.evidencias.all():
            total += evidencia.costo or Decimal("0.00")

        avaluo.costo_reparacion = f"{total:.2f}"
        avaluo.save(update_fields=["costo_reparacion", "actualizado"])

    @transaction.atomic
    def create(self, validated_data):
        evidencias_nuevas = validated_data.pop("_evidencias_nuevas", [])
        evidencias_metadata = validated_data.pop("_evidencias_metadata", [])
        evidencias_existentes = validated_data.pop("_evidencias_existentes", [])
        delete_ids = validated_data.pop("_delete_evidencia_ids", [])
        conceptos = validated_data.pop("_conceptos", [])
        validated_data.pop("_conceptos_recibidos", None)
        checklist_100 = validated_data.pop("_checklist_100", {})
        validated_data.pop("_checklist_recibido", None)

        validated_data.pop("delete_evidencia_ids", None)
        validated_data.pop("conceptos_json", None)
        validated_data.pop("evidencias_metadata_json", None)
        validated_data.pop("evidencias_existentes_json", None)
        validated_data.pop("checklist_100_json", None)

        cliente = self._resolver_cliente(validated_data)

        if checklist_100:
            validated_data["checklist_100"] = checklist_100

        avaluo = AvaluoUsado.objects.create(cliente=cliente, **validated_data)

        if delete_ids:
            avaluo.evidencias.filter(id__in=delete_ids).delete()

        self._crear_evidencias(avaluo, evidencias_nuevas, evidencias_metadata)
        self._actualizar_evidencias_existentes(avaluo, evidencias_existentes)
        self._guardar_conceptos(avaluo, conceptos)
        self._recalcular_total_reparacion(avaluo)

        return avaluo

    @transaction.atomic
    def update(self, instance, validated_data):
        evidencias_nuevas = validated_data.pop("_evidencias_nuevas", [])
        evidencias_metadata = validated_data.pop("_evidencias_metadata", [])
        evidencias_existentes = validated_data.pop("_evidencias_existentes", [])
        delete_ids = validated_data.pop("_delete_evidencia_ids", [])
        conceptos = validated_data.pop("_conceptos", [])
        conceptos_recibidos = validated_data.pop("_conceptos_recibidos", False)
        checklist_100 = validated_data.pop("_checklist_100", {})
        checklist_recibido = validated_data.pop("_checklist_recibido", False)

        validated_data.pop("delete_evidencia_ids", None)
        validated_data.pop("conceptos_json", None)
        validated_data.pop("evidencias_metadata_json", None)
        validated_data.pop("evidencias_existentes_json", None)
        validated_data.pop("checklist_100_json", None)

        usar_cliente = (
            "cliente_id" in validated_data
            or "nombre" in validated_data
            or "telefono" in validated_data
            or "correo" in validated_data
        )

        if usar_cliente:
            cliente = self._resolver_cliente(validated_data)
            instance.cliente = cliente

        campos = [
            "agencia",
            "fecha_avaluo",
            "fecha_finalizacion",
            "fecha_toma_cuenta",
            "agenda_valuacion",
            "asesor_ventas",
            "vendedor",
            "tipo_valuacion",
            "tipo_toma",
            "marca_auto",
            "modelo",
            "anio_modelo",
            "version",
            "serie",
            "placas",
            "kilometraje",
            "color",
            "precio_guia",
            "precio_compra_libro_azul",
            "precio_venta_libro_azul",
            "costo_estimado",
            "costo_mecanica_total",
            "oferta_inicial",
            "oferta_final",
            "origen_valuacion",
            "descripcion",
            "observaciones",
            "comentarios",
            "ganador_subasta",
            "etapa_proceso",
        ]

        for campo in campos:
            if campo in validated_data:
                setattr(instance, campo, validated_data[campo])

        if checklist_recibido:
            checklist_actual = dict(instance.checklist_100 or {})
            checklist_actual.update(checklist_100)
            instance.checklist_100 = checklist_actual

        instance.save()

        if delete_ids:
            instance.evidencias.filter(id__in=delete_ids).delete()

        self._actualizar_evidencias_existentes(instance, evidencias_existentes)

        if evidencias_nuevas:
            self._crear_evidencias(instance, evidencias_nuevas, evidencias_metadata)

        if conceptos_recibidos:
            self._guardar_conceptos(instance, conceptos)

        self._recalcular_total_reparacion(instance)

        return instance