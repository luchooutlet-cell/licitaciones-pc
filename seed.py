"""
Script para cargar 3 licitaciones de prueba.
Uso: python seed.py
"""
from datetime import date, timedelta
from app import app
from models import db, Licitacion

with app.app_context():
    hoy = date.today()

    # Borrar las que ya existan con estos códigos (para poder re-ejecutar)
    codigos = ["PC-001", "PC-002", "PC-003"]
    Licitacion.query.filter(Licitacion.codigo_interno.in_(codigos)).delete(synchronize_session=False)
    db.session.commit()

    ejemplos = [
        Licitacion(
            codigo_interno="PC-001",
            nro_licitacion="YPF-LC-2025-041",
            cliente="YPF",
            yacimiento="Loma Campana",
            provincia="Neuquén",
            estado="Preparando oferta",
            tipo_servicio="Instalación corriente impresa",
            modalidad="Llave en mano",
            fecha_cierre=hoy + timedelta(days=10),
            plazo_ejecucion="120 días",
            moneda="USD",
            presupuesto_oficial=250000,
            nuestra_oferta=235000,
            clausula_ajuste="CAC",
            forma_pago="30 días FF",
            servicios_incluidos="Ingeniería, suministro, montaje y puesta en marcha",
            equipos_requeridos="1 rectificador 50V/30A, 3 lechos de ánodos",
            normativa="NACE SP0169, ISO 15589",
            descripcion="Sistema de PC para 3 ductos colectores en Loma Campana",
            contacto_cliente="Juan Pérez",
            email_contacto="jperez@ypf.com",
        ),
        Licitacion(
            codigo_interno="PC-002",
            nro_licitacion="PAE-GSJ-2025-012",
            cliente="PAE",
            yacimiento="Golfo San Jorge",
            provincia="Santa Cruz",
            estado="Enviada",
            tipo_servicio="Medición CIPS / DCVG / PCM",
            fecha_cierre=hoy + timedelta(days=3),
            moneda="USD",
            presupuesto_oficial=85000,
            nuestra_oferta=79000,
            clausula_ajuste="Sin ajuste",
            forma_pago="Contado",
            descripcion="Relevamiento CIPS/DCVG en 45 km de ducto",
        ),
        Licitacion(
            codigo_interno="PC-003",
            nro_licitacion="VISTA-BPO-2025-007",
            cliente="Vista Energy",
            yacimiento="Bajada del Palo Oeste",
            provincia="Neuquén",
            estado="En análisis",
            tipo_servicio="Diseño PC ductos nuevos",
            fecha_cierre=hoy + timedelta(days=25),
            moneda="USD",
            presupuesto_oficial=420000,
            nuestra_oferta=395000,
            clausula_ajuste="IPC",
            forma_pago="30/60/90 días",
            descripcion="Ingeniería básica y de detalle para PC de ductos nuevos",
        ),
    ]

    for e in ejemplos:
        db.session.add(e)
    db.session.commit()

    print(f"✅ {len(ejemplos)} licitaciones de prueba cargadas:")
    for e in ejemplos:
        print(f"   - {e.codigo_interno} · {e.cliente} · cierre {e.fecha_cierre}")