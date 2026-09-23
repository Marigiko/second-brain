#!/usr/bin/env python3
"""
sb_notes.py - Capa de LECTURA compartida por refinement.py y deduplication.py.

Este modulo no escribe en ninguna nota. Ni en los buffers `.second-brain/` de
los proyectos ni en el vault de Obsidian. Los dos scripts que lo usan son
depuradores que *reportan*: la unica escritura permitida es el reporte en
`logs/`.

Que aporta:

  - lectura de `config.json` y del frontmatter YAML de una nota;
  - un espejo minimo del routing de `vault-paths.js`, para saber en que ruta
    del vault deberia estar una nota del buffer;
  - lectura de las notas del vault, distinguiendo las CURADAS a mano de las que
    entraron por sync a la `Bandeja de entrada`;
  - tokenizacion y similitud coseno con IDF, usadas por deduplication.py.

OJO con el espejo del routing: la fuente de verdad es `src/vault-paths.js`
(funciones `resolveArea` y `resolveTarget`). Aca se replica solo la parte que
hace falta para *ubicar* una nota, porque estos scripts son de Python y no se
puede importar el modulo JS. Si cambia la regla alla, hay que cambiarla aca.
"""

import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
LOGS_DIR = BASE_DIR / "logs"
SECOND_BRAIN_DIR = ".second-brain"
CATEGORIES = ["diario", "decisiones", "aprendizajes", "convenciones", "arquitectura"]


# --------------------------------------------------------------------------
# Config y frontmatter
# --------------------------------------------------------------------------

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def read_frontmatter(content):
    """Devuelve (frontmatter, cuerpo). Si no hay frontmatter valido, ({}, content)."""
    match = re.match(r"^---\n([\s\S]*?)\n---", content)
    if not match:
        return {}, content
    try:
        fm = yaml.safe_load(match.group(1)) or {}
        if not isinstance(fm, dict):
            return {}, content
        return fm, content[match.end():]
    except yaml.YAMLError:
        return {}, content


def note_date(frontmatter):
    """Fecha canonica de una nota, en YYYY-MM-DD.

    `created` es el campo canonico desde el 2026-08-27; `date` queda como
    fallback para las notas escritas antes (duplicaba a `created` y por eso
    se elimino del template).
    """
    raw = frontmatter.get("created") or frontmatter.get("date") or ""
    return str(raw)[:10]


def note_age_days(frontmatter, now=None):
    """Edad en dias segun `created`, o None si la nota no tiene fecha usable."""
    raw = str(frontmatter.get("created") or frontmatter.get("date") or "")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return ((now or datetime.now()) - parsed.replace(tzinfo=None)).days


def note_title(frontmatter, body, filename):
    """Titulo de la nota: `title` del frontmatter, si no el primer H1, si no el slug."""
    title = frontmatter.get("title")
    if title:
        return " ".join(str(title).split())
    heading = re.search(r"^#\s+(.+)$", body, re.M)
    if heading:
        return heading.group(1).strip()
    return Path(filename).stem.replace("-", " ")


# --------------------------------------------------------------------------
# Routing (espejo de vault-paths.js)
# --------------------------------------------------------------------------

def safe_folder(name):
    return re.sub(r'[\\/:*?"<>|]', "-", str(name)).strip()


def resolve_area(project, category):
    """'conocimiento' solo si el proyecto lo pidio explicito; si no, 'proyectos'.

    Espejo de `vault-paths.js:resolveArea`. El default es siempre `proyectos`:
    un agente no puede decidir por nota si algo trasciende al proyecto.
    """
    cats = project.get("knowledge_categories") or []
    if project.get("knowledge_domain") and category in cats:
        return "conocimiento"
    return "proyectos"


def resolve_target(project, category, filename, config):
    """Ruta de la nota dentro del vault, relativa a la raiz. Espejo de `resolveTarget`."""
    area = resolve_area(project, category)
    area_folder = config["vault"]["areas"][area]

    if area == "conocimiento":
        container = safe_folder(project["knowledge_domain"])
        subfolder = config["routing"].get("knowledge_inbox") or "Bandeja de entrada"
    else:
        container = safe_folder(project.get("vault_folder") or project["name"])
        cat_cfg = (config["routing"].get("categories") or {}).get(category) or {}
        subfolder = cat_cfg.get("subfolder") or category.capitalize()

    parts = [area_folder, container, subfolder]
    if filename:
        parts.append(filename)
    return "/".join(p for p in parts if p)


def container_of(project, category, config):
    """Carpeta contenedora del vault (dominio o carpeta de proyecto) como (area, nombre).

    Es la unidad de comparacion natural: todas las notas que caen en el mismo
    contenedor compiten entre si. `scrap` y `scrap-dev-mario` comparten el
    dominio `Scraping Legal`, asi que sus notas caen en el mismo contenedor y
    se comparan entre proyectos.
    """
    area = resolve_area(project, category)
    if area == "conocimiento":
        return area, safe_folder(project["knowledge_domain"])
    return area, safe_folder(project.get("vault_folder") or project["name"])


# --------------------------------------------------------------------------
# Lectura de notas
# --------------------------------------------------------------------------

def _load_note(path, **extra):
    content = Path(path).read_text(encoding="utf-8", errors="replace")
    fm, body = read_frontmatter(content)
    note = {
        "path": str(path),
        "filename": Path(path).name,
        "frontmatter": fm,
        "body": body,
        "title": note_title(fm, body, Path(path).name),
    }
    note.update(extra)
    return note


def project_notes(project, config, categories=None):
    """Notas del buffer `.second-brain/` de un proyecto."""
    sb_dir = Path(project["path"]) / SECOND_BRAIN_DIR
    if not sb_dir.exists():
        return []

    notes = []
    for category in (categories or CATEGORIES):
        cat_dir = sb_dir / category
        if not cat_dir.exists():
            continue
        for md_file in sorted(cat_dir.glob("*.md")):
            notes.append(_load_note(
                md_file,
                category=category,
                origen="buffer",
                proyecto=project["name"],
                destino_vault=resolve_target(project, category, md_file.name, config),
            ))
    return notes


def vault_root(config):
    return Path(config["obsidian"]["vault_path"])


def vault_notes(config, area, container):
    """Notas del vault bajo `<area>/<container>/`, recursivo.

    `curada` marca lo que NO entro por sync: la taxonomia de un dominio
    (`Problemas/`, `Soluciones/`, `Paises/`...) se cura a mano, y todo lo que
    sincroniza el motor cae en `Bandeja de entrada/`. La distincion importa
    porque dos notas curadas que se parecen (un `P37` y su `S35`) estan
    emparejadas a proposito y no son un duplicado.
    """
    area_folder = config["vault"]["areas"][area]
    inbox = config["routing"].get("knowledge_inbox") or "Bandeja de entrada"
    root = vault_root(config) / area_folder / container
    if not root.exists():
        return []

    notes = []
    for md_file in sorted(root.rglob("*.md")):
        rel = md_file.relative_to(vault_root(config))
        es_inbox = inbox in rel.parts
        es_moc = md_file.name.startswith("00 - ")
        notes.append(_load_note(
            md_file,
            category=None,
            origen="vault",
            proyecto=None,
            ruta_vault=str(rel).replace("\\", "/"),
            en_bandeja=es_inbox,
            curada=(not es_inbox and not es_moc),
            es_moc=es_moc,
        ))
    return notes


# --------------------------------------------------------------------------
# Texto y similitud
# --------------------------------------------------------------------------

# Palabras funcionales del espanol que aparecen en casi toda nota y no
# distinguen un tema de otro. La lista es corta a proposito: el IDF ya
# castiga lo que se repite en todo el corpus.
STOPWORDS = set("""
para pero como cuando donde porque desde entre sobre hasta cada este esta esto
estos estas todo toda todos todas otro otra otros otras mismo misma tiene
tienen tener hacer hace hacen puede pueden solo sola tambien nota notas caso
ejemplo decir dice dicen entonces despues antes ahora asi bien cosa cosas veces
parte partes forma formas algo nada cual cuales quien quienes cuanto cuantos
segun aunque mientras pues sino salvo relacionado
""".split())


def strip_accents(text):
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()


def tokens(text):
    """Palabras de contenido: >=4 letras, sin acentos, sin stopwords, sin numeros puros.

    Los numeros se descartan porque son datos del caso (`2646 docs`, `ORD-4370`)
    y no del tema: al medir, el IDF los premiaba por raros y llenaba el nucleo
    de cada nota con identificadores irrepetibles.
    """
    words = re.findall(r"[a-z0-9]{4,}", strip_accents(text).lower())
    return [w for w in words if w not in STOPWORDS and not w.isdigit()]


class TfIdf:
    """Vectores TF-IDF normalizados sobre un corpus fijo, para similitud coseno."""

    def __init__(self, documentos):
        self.n = max(len(documentos), 1)
        counters = [Counter(tokens(d)) for d in documentos]
        df = Counter()
        for c in counters:
            df.update(c.keys())
        self.idf = {w: math.log((self.n + 1) / (v + 1)) for w, v in df.items()}
        self.vectors = [self._unit(c) for c in counters]

    def _unit(self, counter):
        vec = {w: (1 + math.log(c)) * self.idf.get(w, math.log(self.n + 1))
               for w, c in counter.items()}
        norm = math.sqrt(sum(x * x for x in vec.values())) or 1.0
        return {w: x / norm for w, x in vec.items()}

    def cosine(self, i, j):
        a, b = self.vectors[i], self.vectors[j]
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(w, 0.0) for w, x in a.items())


def jaccard(set_a, set_b):
    set_a, set_b = set(set_a), set(set_b)
    union = set_a | set_b
    return len(set_a & set_b) / len(union) if union else 0.0


# --------------------------------------------------------------------------
# Reporte
# --------------------------------------------------------------------------

def write_report(filename, lines):
    """Escribe el reporte en `logs/`. Es el UNICO archivo que estos scripts crean."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGS_DIR / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
