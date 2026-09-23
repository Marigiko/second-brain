#!/usr/bin/env python3
"""
Refinement Engine - reporta el estado de curaduria de las notas, cada 3 dias.

QUE HACE Y QUE NO HACE
----------------------
Detecta y reporta. NO borra, NO archiva, NO consolida y NO escribe en ninguna
nota: ni en los buffers `.second-brain/` ni en el vault. Un depurador
automatico no decide que conocimiento sobra; el humano decide. Lo unico que
este script escribe es `logs/refinement-report.md`.

Antes hacia lo contrario y encima mentia: estampaba `refined: true`,
`refined_at` y `relevance_score` en las notas que caian por debajo de un
umbral, sin mover ni archivar nada, y despues loggeaba "Refinamiento
completado" como si hubiera pasado algo.

POR QUE SE SACO `calculate_relevance_score`
-------------------------------------------
Calculaba `0.5 + tags*0.1 + bonus por largo + 0.2 si la categoria era
decisiones/arquitectura - 0.2 si tenia mas de 30 dias`. Ninguno de esos
terminos mide relevancia:

  - contar tags premia poner tags, no tener razon: una nota vacia con 5 tags
    sacaba 0.8;
  - el largo del cuerpo no es valor - la nota mas util del vault puede ser un
    parrafo con una medicion;
  - la antiguedad no es demerito en una base de conocimiento: es justo al reves,
    una nota que sigue siendo cierta a los seis meses vale mas, no menos;
  - la categoria no dice nada de la nota individual.

En su lugar no hay puntaje. Hay SENALES binarias y verificables, cada una con
su justificacion. Una senal no condena a la nota: le dice al humano donde mirar.

  1. `nunca-llego-al-vault`  la nota dice `synced` pero el archivo no existe en
     la ruta que le corresponde en el vault. Objetivo (se chequea el archivo) y
     es el fallo mas caro: el conocimiento existe solo en el buffer local.
  2. `sync-atascado`         `sync_status` distinto de `synced`, o `last_error`
     pegado en el frontmatter. La nota no esta publicada o arrastra un error.
  3. `sin-titulo`            sin `title` en el frontmatter y sin encabezado H1.
     Sin titulo no se puede encontrar ni destilar; la convencion del vault es
     que el titulo dice la conclusion.
  4. `sin-tags`              sin tags no entra en ninguna busqueda por tag.
  5. `sin-medicion`          el cuerpo no tiene un solo digito. La convencion
     del vault es "el titulo dice la conclusion y el cuerpo trae la medicion";
     una nota sin ningun numero no cumple su propia regla. Es una senal debil a
     proposito: hay conclusiones legitimas sin numero, por eso reporta y no
     descarta.
  6. `cuerpo-minimo`         menos de 400 caracteres de prosa (sin frontmatter,
     encabezados ni bloques de codigo). NO es una escala de calidad: es un piso
     que detecta la nota que quedo sin cuerpo. El corte sale de medir los
     buffers: los cuerpos reales van de 1389 a 5093 caracteres y los dos stubs
     tienen 35 y 60. Cualquier corte dentro de ese hueco separa lo mismo.
  7. `sin-enlaces`           sin `[[wikilinks]]` salientes: nota inalcanzable
     navegando el grafo, que es como se usa el vault.
  8. `plantilla-sin-llenar`  quedaron marcadores tipo TODO / TBD / REEMPLAZA.

SOBRE EL UMBRAL DE EDAD
-----------------------
`min_note_age_days` (config.json) sigue filtrando las senales de curaduria: una
nota de ayer todavia no tuvo oportunidad de curarse. Lo que estaba mal no era el
umbral sino el log, que decia "Notas a evaluar: 0" sin distinguir "no hay nada
con edad suficiente" de "evalue y no encontre nada". Ahora se reportan los dos
numeros por separado.

Las senales 1 y 2 NO pasan por el umbral de edad: una nota que no llego al vault
hay que verla hoy, no dentro de una semana.

POR QUE SE SACO `consolidate_daily_notes`
-----------------------------------------
La funcion fusionaba las notas de diario de una semana en un `semanal-YYYY-Www.md`
nuevo, reescribia el frontmatter de las originales y devolvia una lista que el
llamador asignaba a una variable que nunca usaba. O sea: codigo muerto con
efecto de escritura.

Se saca la consolidacion automatica, no la senal. Motivos:

  - viola el principio: fusionar es decidir que conocimiento sobra;
  - duplicaba contenido - el `semanal-*.md` nacia con `sync_status: pending`, se
    sincronizaba al vault como nota nueva y quedaba conviviendo con las diarias,
    que el sync ya appendea a la nota del dia;
  - su resultado no se usaba, asi que el unico efecto real era escribir.

Lo que se conserva es el aviso: el reporte lista las semanas con varias notas de
diario, para que el humano las consolide si quiere.
"""

import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sb_notes as sb

# Piso de prosa util. Ver senal 6 del docstring: sale de medir los buffers, no
# es una escala de calidad.
MIN_PROSA_CHARS = 400

# Cuantas notas de diario en una misma semana ameritan sugerir una consolidacion
# manual. Es el mismo numero que usaba la consolidacion automatica.
MIN_DIARIOS_POR_SEMANA = 3

MARCADORES_PLANTILLA = ("TODO", "TBD", "FIXME", "REEMPLAZA", "XXX", "PENDIENTE:")

REPORTE = "refinement-report.md"


def prosa_util(body):
    """Cuerpo sin encabezados, bloques de codigo, citas ni frontmatter."""
    texto = re.sub(r"```[\s\S]*?```", "", body)
    texto = re.sub(r"^#+ .*$", "", texto, flags=re.M)
    return texto.strip()


def senales_de_curaduria(note):
    """Senales que exigen que la nota haya tenido tiempo de curarse."""
    fm = note["frontmatter"]
    body = note["body"]
    encontradas = []

    if not fm.get("title") and not re.search(r"^#\s+", body, re.M):
        encontradas.append("sin-titulo")
    if not (fm.get("tags") or []):
        encontradas.append("sin-tags")
    if not re.search(r"\d", body):
        encontradas.append("sin-medicion")
    if len(prosa_util(body)) < MIN_PROSA_CHARS:
        encontradas.append("cuerpo-minimo")
    if not re.search(r"\[\[[^\]]+\]\]", body):
        encontradas.append("sin-enlaces")
    if any(m in body for m in MARCADORES_PLANTILLA):
        encontradas.append("plantilla-sin-llenar")

    return encontradas


def senales_de_publicacion(note, vault_root):
    """Senales sobre si la nota llego al vault. No dependen de la edad."""
    fm = note["frontmatter"]
    encontradas = []

    estado = fm.get("sync_status")
    if estado != "synced":
        encontradas.append(f"sync-atascado({estado or 'sin-estado'})")
    elif fm.get("last_error"):
        encontradas.append("sync-atascado(error-residual)")

    destino = note.get("destino_vault")
    if destino and not (vault_root / destino).exists():
        encontradas.append("nunca-llego-al-vault")

    return encontradas


def semanas_de_diario(notes):
    """Semanas con varias notas de diario. Solo informa: no consolida nada."""
    semanas = defaultdict(list)
    for note in notes:
        if note.get("category") != "diario":
            continue
        fecha = sb.note_date(note["frontmatter"])
        try:
            semanas[datetime.strptime(fecha, "%Y-%m-%d").strftime("%Y-W%W")].append(note)
        except ValueError:
            continue
    return {k: v for k, v in semanas.items() if len(v) >= MIN_DIARIOS_POR_SEMANA}


def backlog_bandeja(config):
    """Cuantas notas del dominio siguen sin destilar en la Bandeja de entrada.

    Es la unica metrica del vault que este reporte mide y que hoy no media
    nadie. Todo lo que el sync manda a `Conocimiento/` cae en una sola bandeja
    a proposito (la taxonomia del dominio se cura a mano), asi que la bandeja
    crece sola y nadie se entera hasta que es inmanejable.
    """
    dominios = {}
    for project in config["projects"]:
        dominio = project.get("knowledge_domain")
        if project.get("enabled", True) and dominio:
            dominios.setdefault(sb.safe_folder(dominio), set()).add(project["name"])

    resultado = []
    for dominio, proyectos in sorted(dominios.items()):
        # El MOC (`00 - Mapa del dominio.md`) es el indice de la carpeta, no una
        # nota del dominio: contarlo inflaba el total contra el que se mide el
        # backlog y no coincidia con el corpus de deduplication.py.
        notas = [n for n in sb.vault_notes(config, "conocimiento", dominio)
                 if not n.get("es_moc")]
        if not notas:
            continue
        bandeja = [n for n in notas if n.get("en_bandeja")]
        con_fecha = []
        for n in bandeja:
            edad = sb.note_age_days(n["frontmatter"])
            if edad is not None:
                con_fecha.append((edad, n))
        # Por edad descendente y, a igual edad, por nombre: dos notas del mismo
        # dia no se pueden comparar entre si y el orden tiene que ser estable.
        con_fecha.sort(key=lambda par: (-par[0], par[1]["filename"]))
        resultado.append({
            "dominio": dominio,
            "proyectos": sorted(proyectos),
            "total": len(notas),
            "bandeja": len(bandeja),
            "curadas": sum(1 for n in notas if n.get("curada")),
            "sin_fecha": len(bandeja) - len(con_fecha),
            "mas_viejas": con_fecha[:10],
        })
    return resultado


def run_refinement():
    config = sb.load_config()
    min_age = config["refinement"]["min_note_age_days"]
    vault_root = sb.vault_root(config)
    inicio = datetime.now()

    print(f"[{inicio.isoformat()}] Iniciando refinamiento (solo reporta, no escribe notas)...")
    print(f"  Vault: {vault_root}  ·  umbral de edad: {min_age} dias")

    lineas = [
        "---",
        "tags: [second-brain, reporte, refinamiento]",
        f"created: {inicio.strftime('%Y-%m-%d')}",
        "---",
        "",
        "# Refinamiento - que necesita tu atencion",
        "",
        f"Corrida: {inicio.isoformat(timespec='seconds')}  ·  "
        f"umbral de edad: {min_age} dias  ·  piso de prosa: {MIN_PROSA_CHARS} caracteres",
        "",
        "> Este reporte no borra, no archiva y no toca ninguna nota. Marca donde mirar.",
        "",
        "## 1. Resumen por proyecto",
        "",
        "| Proyecto | Notas | Sin edad suficiente | Evaluadas | Con senales |",
        "|---|---:|---:|---:|---:|",
    ]

    detalle = []
    publicacion = []
    diarios = []
    total = {"notas": 0, "jovenes": 0, "evaluadas": 0, "con_senales": 0}

    for project in config["projects"]:
        if not project.get("enabled", True):
            continue

        notes = sb.project_notes(project, config)
        if not notes:
            continue

        jovenes = 0
        evaluadas = 0
        con_senales = 0

        for note in notes:
            fallos_pub = senales_de_publicacion(note, vault_root)
            if fallos_pub:
                publicacion.append((project["name"], note, fallos_pub))

            edad = sb.note_age_days(note["frontmatter"])
            if edad is None or edad < min_age:
                jovenes += 1
                continue

            evaluadas += 1
            fallos = senales_de_curaduria(note)
            if fallos:
                con_senales += 1
                detalle.append((project["name"], note, edad, fallos))

        semanas = semanas_de_diario(notes)
        if semanas:
            diarios.append((project["name"], semanas))

        total["notas"] += len(notes)
        total["jovenes"] += jovenes
        total["evaluadas"] += evaluadas
        total["con_senales"] += con_senales

        # El log distingue los dos casos que antes se confundian en un solo cero.
        print(f"\nProyecto: {project['name']}")
        print(f"  Notas en el buffer: {len(notes)}")
        print(f"  Sin edad suficiente (< {min_age}d), no evaluables: {jovenes}")
        if evaluadas == 0:
            print("  Evaluadas: 0 - no hay ninguna nota que ya haya cumplido el umbral")
        else:
            print(f"  Evaluadas: {evaluadas} - con al menos una senal: {con_senales}")

        lineas.append(
            f"| {project['name']} | {len(notes)} | {jovenes} | {evaluadas} | {con_senales} |"
        )

    lineas.append(
        f"| **total** | **{total['notas']}** | **{total['jovenes']}** | "
        f"**{total['evaluadas']}** | **{total['con_senales']}** |"
    )
    lineas.append("")
    if total["evaluadas"] == 0 and total["notas"] > 0:
        lineas.append(
            f"Ninguna nota supera los {min_age} dias todavia: no es que se evaluaron y "
            "salieron limpias, es que no habia nada que evaluar."
        )
        lineas.append("")

    # ---- Publicacion -------------------------------------------------------
    lineas += ["## 2. Notas que no estan publicadas en el vault", ""]
    if not publicacion:
        lineas.append("Ninguna. Todas las notas de los buffers existen en su ruta del vault.")
    else:
        lineas.append("Estas notas viven solo en el buffer local. Que hacer: correr el sync "
                      "(`node src/sync-engine.js`) y, si vuelve a fallar, mirar `last_error`.")
        lineas.append("")
        lineas.append("| Proyecto | Nota | Senales | Destino esperado |")
        lineas.append("|---|---|---|---|")
        for proyecto, note, fallos in publicacion:
            lineas.append(
                f"| {proyecto} | `{note['filename']}` | {', '.join(fallos)} | "
                f"`{note.get('destino_vault', '?')}` |"
            )
    lineas.append("")

    # ---- Senales de curaduria ---------------------------------------------
    lineas += ["## 3. Senales de curaduria", ""]
    if total["evaluadas"] == 0:
        lineas.append("Sin notas evaluables en esta corrida.")
    elif not detalle:
        lineas.append(f"Se evaluaron {total['evaluadas']} notas y ninguna dio senal.")
    else:
        lineas.append(
            f"Se evaluaron {total['evaluadas']} notas; {len(detalle)} dieron al menos una "
            "senal. Una senal no condena la nota: dice donde mirar."
        )
        lineas.append("")
        lineas.append("| Proyecto | Nota | Edad | Senales |")
        lineas.append("|---|---|---:|---|")
        for proyecto, note, edad, fallos in sorted(detalle, key=lambda x: -len(x[3])):
            lineas.append(
                f"| {proyecto} | `{note['filename']}` | {edad}d | {', '.join(fallos)} |"
            )
    lineas.append("")

    # ---- Diario ------------------------------------------------------------
    lineas += ["## 4. Semanas de diario con varias notas", ""]
    if not diarios:
        lineas.append(f"Ninguna semana llega a {MIN_DIARIOS_POR_SEMANA} notas de diario.")
    else:
        lineas.append(
            "Sugerencia, no accion: estas semanas concentran varias notas de diario y "
            "podrian resumirse a mano. El script ya no las fusiona solo."
        )
        lineas.append("")
        for proyecto, semanas in diarios:
            for semana, notas in sorted(semanas.items()):
                archivos = ", ".join(f"`{n['filename']}`" for n in notas)
                lineas.append(f"- **{proyecto}** · {semana} · {len(notas)} notas: {archivos}")
    lineas.append("")

    # ---- Bandeja de entrada -----------------------------------------------
    lineas += ["## 5. Backlog de la bandeja de entrada del vault", ""]
    backlog = backlog_bandeja(config)
    if not backlog:
        lineas.append("Ningun proyecto declara `knowledge_domain`, asi que no hay bandeja.")
    else:
        for b in backlog:
            pct = (100.0 * b["bandeja"] / b["total"]) if b["total"] else 0.0
            print(f"\nBandeja de entrada · {b['dominio']}: "
                  f"{b['bandeja']} sin destilar de {b['total']} notas ({pct:.0f}%)")
            lineas.append(f"### {b['dominio']}")
            lineas.append("")
            lineas.append(f"Proyectos que alimentan el dominio: {', '.join(b['proyectos'])}")
            lineas.append("")
            lineas.append(
                f"- **{b['bandeja']} notas sin destilar** de {b['total']} en el dominio "
                f"({pct:.0f}%); {b['curadas']} ya estan curadas en la taxonomia."
            )
            if b["sin_fecha"]:
                lineas.append(f"- {b['sin_fecha']} sin `created` usable (no se puede fechar).")
            if b["mas_viejas"]:
                # `created` es la fecha en que se escribio la nota, no la fecha en
                # que entro a la bandeja: el frontmatter no registra el momento del
                # sync, asi que esto es una cota inferior del tiempo de espera.
                lineas.append(
                    f"- La mas vieja se escribio hace {b['mas_viejas'][0][0]} dias."
                )
                lineas.append("")
                lineas.append("Las mas viejas sin destilar (edad por `created`):")
                lineas.append("")
                lineas.append("| Edad (dias) | Nota |")
                lineas.append("|---:|---|")
                for edad, nota in b["mas_viejas"]:
                    lineas.append(f"| {edad} | `{nota['filename']}` |")
            lineas.append("")
            lineas.append(
                "Que hacer: mover cada nota a la carpeta del dominio que le corresponde "
                "(`Problemas/`, `Soluciones/`, ...). La taxonomia se cura a mano a proposito; "
                "el sync nunca la toca."
            )
            lineas.append("")

    ruta = sb.write_report(REPORTE, lineas)
    print(f"\n[{datetime.now().isoformat()}] Refinamiento completado. Reporte: {ruta}")


if __name__ == "__main__":
    run_refinement()
