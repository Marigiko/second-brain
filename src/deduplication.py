#!/usr/bin/env python3
"""
Deduplication Engine - busca notas duplicadas y las REPORTA, cada 3 dias.

QUE HACE Y QUE NO HACE
----------------------
Detecta y reporta. NO fusiona, NO borra y NO escribe en ninguna nota - ni en los
buffers `.second-brain/` ni en el vault. Un depurador automatico no decide que
conocimiento sobra. Lo unico que escribe es `logs/dedup-report.md`.

Lo que hacia antes, y por que no servia:

  1. La rama que importaba no existia. `merge_or_cross_reference` devolvia
     'merge' cuando las dos notas eran del mismo proyecto, y el loop solo
     implementaba 'cross-reference'. Un duplicado dentro del mismo proyecto se
     detectaba y se descartaba EN SILENCIO. Por eso el log decia "Pares
     similares encontrados: 1" el 2026-08-16, el 2026-08-28 y el 2026-09-01:
     era el mismo par las tres veces (`test-sync` <-> `test-sync-2`), sin accion.
     Ahora no hay ramas: todo par que pasa el umbral se reporta, y la etiqueta
     de relacion (mismo proyecto / entre proyectos / contra el vault) es un dato
     del reporte, no una decision del script.

  2. Comparaba solo tags con Jaccard >= 0.5. Eso mide parecido tematico, no
     duplicacion: medido sobre los buffers daba 10 pares y casi todos eran notas
     hermanas legitimas sobre el mismo tema. Los tags siguen como senal de
     contexto, con peso 0 en el ranking.

  3. Miraba solo los buffers locales, nunca el vault. Eso dejo pasar un
     duplicado real: `re-ingestar-o-el-batch-miente.md` (buffer de
     scrap-dev-mario, 2026-09-02) duplica el nucleo de
     `bumpear-el-batchid-es-reingestar.md`, que estaba en el vault desde el
     2026-08-31 y venia de OTRO proyecto. El dominio `Scraping Legal` es
     compartido entre `scrap` y `scrap-dev-mario`, asi que comparar dentro del
     buffer de un proyecto nunca lo iba a encontrar.

COMO COMPARA AHORA
------------------
El corpus es el CONTENEDOR del vault, no el proyecto: todas las notas que
terminan en la misma carpeta compiten entre si. `scrap` y `scrap-dev-mario`
comparten `Conocimiento/Scraping Legal/`, asi que sus notas se comparan entre
si y contra las 100+ notas curadas del dominio que ya estaban en el vault.

Cada nota del buffer se une con su copia del vault por la ruta de destino que
resuelve el routing: una nota ya sincronizada NO es un duplicado de si misma.

SENALES Y UMBRAL (medido sobre el corpus real, 152 notas del dominio + buffers)
-------------------------------------------------------------------------------
  - `titulo`: coseno TF-IDF sobre el titulo. Es la senal mas fuerte del ranking
    porque la convencion del vault es que el titulo dice la CONCLUSION: dos
    notas con la misma conclusion son el caso a revisar. Sola, deja el duplicado
    real conocido en el puesto 19 de 6120 pares.
  - `cuerpo`: coseno TF-IDF sobre el cuerpo. Aporta el caso del copy-paste, que
    el titulo no ve.
  - `tags`: Jaccard, informativo. Peso 0: medido, es la senal que mas falsos
    positivos genera (notas hermanas comparten casi todos los tags).

  score = 0.5 * titulo + 0.5 * cuerpo

Distribucion medida sobre los 6120 pares evaluables: p50 = 0.019, p99 = 0.109,
p999 = 0.231. El duplicado real conocido saca 0.133 (puesto 31 de 6120, el 0.5%
mas alto).

POR QUE EL REPORTE ES UN RANKING Y NO UN VEREDICTO
--------------------------------------------------
Esto se midio antes de elegir el formato, y el resultado obliga: el duplicado
real conocido es una PARAFRASIS - las dos notas cuentan el mismo mecanismo con
vocabulario distinto y casos distintos (`BR/tceSc` contra `AR/digestoLaCosta`).
Comparten dos terminos tecnicos en total. Ningun umbral lo separa de las notas
hermanas legitimas: cualquier corte que lo incluya arrastra decenas de pares
tematicos.

Lo que si funciona, medido: pedirle a cada nota sin curar sus VECINOS mas
cercanos. Con los 3 mas cercanos por nota, el par real aparece - en el puesto 2
de las dos notas, en las dos direcciones. Son 48 bloques de 3 lineas: un humano
los lee. Un booleano "es duplicado" habria seguido mintiendo, en la direccion
contraria a antes.

`UMBRAL_FUERTE` marca aparte los pares que ademas superan p999. Es una ayuda de
lectura para empezar por algun lado, no un veredicto.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sb_notes as sb

# Categorias que se deduplican. `diario` queda afuera: es un registro
# cronologico y dos entradas de dias distintos sobre el mismo tema no son un
# duplicado, son el diario funcionando.
CATEGORIAS = ["decisiones", "aprendizajes", "convenciones", "arquitectura"]

# Ver "SENALES Y UMBRAL" en el docstring. Los pesos y los cortes salen de medir
# el corpus real, no de una intuicion.
PESO_TITULO = 0.5
PESO_CUERPO = 0.5
VECINOS_POR_NOTA = 3
UMBRAL_REPORTE = 0.06      # debajo de esto el vecino no dice nada (p50 = 0.019)
UMBRAL_FUERTE = 0.23       # p999 del corpus medido

REPORTE = "dedup-report.md"


def construir_corpus(config):
    """Agrupa notas por contenedor del vault, uniendo cada nota con su copia sincronizada.

    Devuelve {(area, contenedor): [entidad, ...]}. Una entidad es una nota
    logica: si esta en un buffer y ya se sincronizo, sus dos archivos son la
    misma entidad y no se comparan entre si.
    """
    corpus = {}

    # 1. Notas de los buffers, con la ruta del vault que les corresponde.
    for project in config["projects"]:
        if not project.get("enabled", True):
            continue
        for note in sb.project_notes(project, config, CATEGORIAS):
            clave = sb.container_of(project, note["category"], config)
            grupo = corpus.setdefault(clave, {})
            destino = note["destino_vault"]
            entidad = grupo.get(destino)
            if entidad is None:
                grupo[destino] = {
                    "titulo": note["title"],
                    "cuerpo": note["body"],
                    "frontmatter": note["frontmatter"],
                    "filename": note["filename"],
                    "curada": False,
                    "proyectos": {project["name"]},
                    "origenes": [f"buffer:{project['name']}"],
                    "ruta": note["path"],
                }
            else:
                # Dos buffers distintos que resuelven al MISMO archivo del vault:
                # uno le pisa la nota al otro en el proximo sync. Duplicado por
                # construccion, no por parecido.
                entidad["proyectos"].add(project["name"])
                entidad["origenes"].append(f"buffer:{project['name']}")

    # 2. Notas del vault del mismo contenedor. Si la ruta ya la ocupa una nota
    #    del buffer, es su copia sincronizada: se enriquece, no se duplica.
    for clave in list(corpus.keys()):
        area, contenedor = clave
        grupo = corpus[clave]
        for note in sb.vault_notes(config, area, contenedor):
            if note.get("es_moc"):
                continue
            ruta = note["ruta_vault"]
            entidad = grupo.get(ruta)
            if entidad is not None:
                entidad["origenes"].append("vault")
                continue
            grupo[ruta] = {
                "titulo": note["title"],
                "cuerpo": note["body"],
                "frontmatter": note["frontmatter"],
                "filename": note["filename"],
                "curada": note.get("curada", False),
                "proyectos": set(),
                "origenes": ["vault"],
                "ruta": ruta,
            }

    return {k: list(v.values()) for k, v in corpus.items()}


def relacion(a, b):
    """Etiqueta de contexto del par. Es un dato del reporte, no una decision.

    La etiqueta dice de donde viene cada nota, que es lo que el humano necesita
    para decidir: un duplicado dentro de un proyecto se arregla borrando una;
    uno entre proyectos suele querer una sola nota en el dominio compartido; y
    contra una nota ya curada casi siempre significa "esto va destilado ahi".

    Ninguna de estas etiquetas cambia lo que hace el script. La version vieja
    usaba una decision equivalente ('merge' contra 'cross-reference') para
    descartar en silencio la mitad de los pares.
    """
    if a["curada"] or b["curada"]:
        return "sin-curar vs curada"

    pa, pb = a["proyectos"], b["proyectos"]
    if not pa and not pb:
        # Ninguna tiene buffer vivo: las dos son notas de la bandeja del vault.
        return "ambas en la bandeja"
    if not pa or not pb:
        return "buffer vs bandeja"
    if pa & pb:
        return "mismo proyecto" if len(pa | pb) == 1 else "proyectos solapados"
    return "entre proyectos"


def analizar(entidades):
    """Vecinos mas cercanos de cada nota sin curar, y los pares fuertes del grupo."""
    n = len(entidades)
    if n < 2:
        return [], []

    tf_titulo = sb.TfIdf([e["titulo"] for e in entidades])
    tf_cuerpo = sb.TfIdf([e["cuerpo"] for e in entidades])

    def score(i, j):
        return (PESO_TITULO * tf_titulo.cosine(i, j)
                + PESO_CUERPO * tf_cuerpo.cosine(i, j))

    vecinos = []
    fuertes = {}

    for i in range(n):
        if entidades[i]["curada"]:
            # Dos notas curadas que se parecen estan emparejadas a proposito
            # (un `P37 - problema` con su `S35 - solucion`): al medir, esos
            # pares copaban el top del ranking con coseno 0.80 y no eran
            # duplicados. Solo se buscan vecinos DE lo que no esta curado.
            continue

        candidatos = []
        for j in range(n):
            if i == j:
                continue
            s = score(i, j)
            if s < UMBRAL_REPORTE:
                continue
            candidatos.append((s, j))

        candidatos.sort(reverse=True)
        top = candidatos[:VECINOS_POR_NOTA]
        if top:
            vecinos.append({
                "nota": entidades[i],
                "vecinos": [{
                    "otra": entidades[j],
                    "score": s,
                    "titulo": tf_titulo.cosine(i, j),
                    "cuerpo": tf_cuerpo.cosine(i, j),
                    "tags": sb.jaccard(
                        [str(t).lower() for t in (entidades[i]["frontmatter"].get("tags") or [])],
                        [str(t).lower() for t in (entidades[j]["frontmatter"].get("tags") or [])],
                    ),
                    "relacion": relacion(entidades[i], entidades[j]),
                } for s, j in top],
            })

        for s, j in candidatos:
            if s >= UMBRAL_FUERTE:
                fuertes[tuple(sorted((i, j)))] = s

    pares_fuertes = [{
        "a": entidades[i],
        "b": entidades[j],
        "score": s,
        "titulo": tf_titulo.cosine(i, j),
        "cuerpo": tf_cuerpo.cosine(i, j),
        "relacion": relacion(entidades[i], entidades[j]),
    } for (i, j), s in sorted(fuertes.items(), key=lambda kv: -kv[1])]

    return vecinos, pares_fuertes


def colisiones_de_destino(entidades):
    """Notas de proyectos distintos que resuelven al MISMO archivo del vault."""
    return [e for e in entidades if len(e["proyectos"]) > 1]


def run_deduplication():
    config = sb.load_config()
    inicio = datetime.now()

    print(f"[{inicio.isoformat()}] Iniciando deduplicacion (solo reporta, no fusiona)...")
    print(f"  Vault: {sb.vault_root(config)}")

    corpus = construir_corpus(config)

    lineas = [
        "---",
        "tags: [second-brain, reporte, duplicados]",
        f"created: {inicio.strftime('%Y-%m-%d')}",
        "---",
        "",
        "# Duplicados - candidatos para revisar a mano",
        "",
        f"Corrida: {inicio.isoformat(timespec='seconds')}  ·  "
        f"score = {PESO_TITULO} x titulo + {PESO_CUERPO} x cuerpo (coseno TF-IDF)  ·  "
        f"umbral {UMBRAL_REPORTE}, fuerte {UMBRAL_FUERTE}",
        "",
        "> Este reporte no fusiona, no borra y no toca ninguna nota. Propone pares.",
        "> El score ordena candidatos; no dice que dos notas sean la misma. El",
        "> duplicado real conocido del dominio saca 0.133 y las notas hermanas",
        "> legitimas llegan a 0.34: ningun umbral las separa, por eso se reportan",
        "> los vecinos mas cercanos de cada nota y decide el humano.",
        "",
    ]

    total_vecinos = 0
    total_fuertes = 0
    total_colisiones = 0

    for (area, contenedor), entidades in sorted(corpus.items()):
        sin_curar = sum(1 for e in entidades if not e["curada"])
        curadas = len(entidades) - sin_curar

        vecinos, fuertes = analizar(entidades)
        colisiones = colisiones_de_destino(entidades)

        total_vecinos += len(vecinos)
        total_fuertes += len(fuertes)
        total_colisiones += len(colisiones)

        print(f"\nCorpus {area}/{contenedor}: {len(entidades)} notas "
              f"({sin_curar} sin curar, {curadas} curadas en el vault)")
        print(f"  Pares fuertes (>= {UMBRAL_FUERTE}): {len(fuertes)}")
        print(f"  Notas sin curar con algun vecino cercano: {len(vecinos)} de {sin_curar}")
        if colisiones:
            print(f"  COLISIONES de destino en el vault: {len(colisiones)}")

        lineas += [
            f"## {area}/{contenedor}",
            "",
            f"{len(entidades)} notas comparadas: {sin_curar} sin curar "
            f"(buffers + bandeja de entrada) y {curadas} ya curadas en el vault. "
            f"Una nota del buffer y su copia sincronizada cuentan como una sola.",
            "",
        ]

        if colisiones:
            lineas += [
                "### Colisiones de destino (duplicado seguro)",
                "",
                "Dos proyectos escriben notas distintas en el MISMO archivo del vault: "
                "en el proximo sync una le pisa la nota a la otra.",
                "",
            ]
            for e in colisiones:
                lineas.append(
                    f"- `{e['ruta']}` <- {', '.join(sorted(e['proyectos']))}"
                )
            lineas.append("")

        if fuertes:
            lineas += [
                f"### Pares fuertes (score >= {UMBRAL_FUERTE})",
                "",
                "| Score | Titulo | Cuerpo | Relacion | Notas |",
                "|---:|---:|---:|---|---|",
            ]
            for p in fuertes:
                lineas.append(
                    f"| {p['score']:.3f} | {p['titulo']:.3f} | {p['cuerpo']:.3f} | "
                    f"{p['relacion']} | `{p['a']['filename']}` <-> `{p['b']['filename']}` |"
                )
            lineas.append("")

        if not vecinos:
            lineas += ["Ninguna nota sin curar tiene un vecino por encima del umbral.", ""]
            continue

        lineas += [
            f"### Vecinos mas cercanos de cada nota sin curar (hasta {VECINOS_POR_NOTA})",
            "",
        ]
        for v in sorted(vecinos, key=lambda x: -x["vecinos"][0]["score"]):
            lineas.append(f"**`{v['nota']['filename']}`**")
            origen = ", ".join(v["nota"]["origenes"])
            lineas.append(f"<br>_{v['nota']['titulo']}_ · origen: {origen}")
            lineas.append("")
            lineas.append("| Score | Titulo | Cuerpo | Tags | Relacion | Vecino |")
            lineas.append("|---:|---:|---:|---:|---|---|")
            for x in v["vecinos"]:
                marca = " **[fuerte]**" if x["score"] >= UMBRAL_FUERTE else ""
                lineas.append(
                    f"| {x['score']:.3f}{marca} | {x['titulo']:.3f} | {x['cuerpo']:.3f} | "
                    f"{x['tags']:.2f} | {x['relacion']} | `{x['otra']['filename']}` |"
                )
            lineas.append("")

    if not corpus:
        lineas.append("No hay ningun buffer `.second-brain/` con notas en las categorias "
                      f"{', '.join(CATEGORIAS)}.")

    lineas += [
        "## Que hacer con esto",
        "",
        "- **Colision de destino**: hay que resolverla, una de las dos notas se pierde.",
        "- **Par fuerte**: leer las dos y decidir - fusionar a mano, o dejar las dos con "
        "un `[[enlace]]` entre ellas si cuentan casos distintos del mismo mecanismo.",
        "- **Vecino de una nota de la bandeja**: si el vecino ya esta curado, la nota "
        "nueva probablemente va destilada dentro de esa, no como nota aparte.",
        "- Nada de esto lo hace el script: fusionar es decidir que conocimiento sobra.",
        "",
    ]

    ruta = sb.write_report(REPORTE, lineas)
    print(f"\n  Total: {total_fuertes} pares fuertes, {total_vecinos} notas con vecinos, "
          f"{total_colisiones} colisiones de destino.")
    print(f"[{datetime.now().isoformat()}] Deduplicacion completada. Reporte: {ruta}")


if __name__ == "__main__":
    run_deduplication()
