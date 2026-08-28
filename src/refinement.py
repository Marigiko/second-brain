#!/usr/bin/env python3
"""
Refinement Engine - Consolida y limpia notas cada 3 dias.
Identifica notas de baja relevancia, extrae puntos clave y archiva.
"""

import os
import sys
import json
import yaml
import re
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
SECOND_BRAIN_DIR = ".second-brain"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def read_frontmatter(content):
    match = re.match(r'^---\n([\s\S]*?)\n---', content)
    if not match:
        return {}, content
    try:
        fm = yaml.safe_load(match.group(1)) or {}
        body = content[match.end():]
        return fm, body
    except:
        return {}, content

def write_frontmatter(fm):
    return '---\n' + yaml.dump(fm, allow_unicode=True, default_flow_style=False) + '---\n'

def note_date(frontmatter):
    """Fecha canonica de una nota, en YYYY-MM-DD.

    `created` es el campo canonico desde el 2026-08-27; `date` queda como
    fallback para las notas escritas antes (duplicaba a `created` y por eso
    se elimino del template).
    """
    raw = frontmatter.get('created') or frontmatter.get('date') or ''
    return str(raw)[:10]

def get_all_notes(project_path):
    sb_dir = Path(project_path) / SECOND_BRAIN_DIR
    if not sb_dir.exists():
        return []

    notes = []
    categories = ['diario', 'decisiones', 'aprendizajes', 'convenciones', 'arquitectura']

    for category in categories:
        cat_dir = sb_dir / category
        if not cat_dir.exists():
            continue

        for md_file in cat_dir.glob('*.md'):
            content = md_file.read_text(encoding='utf-8')
            fm, body = read_frontmatter(content)

            notes.append({
                'path': str(md_file),
                'category': category,
                'filename': md_file.name,
                'frontmatter': fm,
                'body': body,
                'content': content
            })

    return notes

def calculate_relevance_score(note):
    score = 0.5
    tags = note['frontmatter'].get('tags', [])
    score += min(len(tags) * 0.1, 0.3)

    body_length = len(note['body'].strip())
    if body_length > 200:
        score += 0.1
    if body_length > 500:
        score += 0.1

    if note['category'] in ['decisiones', 'arquitectura']:
        score += 0.2

    created = note['frontmatter'].get('created', '')
    if created:
        try:
            created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
            age_days = (datetime.now() - created_date.replace(tzinfo=None)).days
            if age_days < 7:
                score += 0.1
            elif age_days > 30:
                score -= 0.2
        except:
            pass

    return min(max(score, 0.0), 1.0)

def should_refine(note, min_age_days):
    created = note['frontmatter'].get('created', '')
    if not created:
        return False
    try:
        created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
        age_days = (datetime.now() - created_date.replace(tzinfo=None)).days
        return age_days >= min_age_days
    except:
        return False

def consolidate_daily_notes(notes):
    diario_notes = [n for n in notes if n['category'] == 'diario']
    if len(diario_notes) < 3:
        return notes

    weeks = {}
    for note in diario_notes:
        date_str = note_date(note['frontmatter'])
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                week_key = date.strftime('%Y-W%W')
                if week_key not in weeks:
                    weeks[week_key] = []
                weeks[week_key].append(note)
            except:
                pass

    consolidated = []
    for week_key, week_notes in weeks.items():
        if len(week_notes) >= 3:
            summary_content = f"# Resumen Semanal {week_key}\n\n"
            for note in sorted(week_notes, key=lambda n: note_date(n['frontmatter'])):
                summary_content += f"\n---\n\n{note['body']}\n"

            for note in week_notes:
                note['frontmatter']['refined'] = True
                note['frontmatter']['consolidated_into'] = f"semanal-{week_key}"
                Path(note['path']).write_text(
                    write_frontmatter(note['frontmatter']) + note['body'],
                    encoding='utf-8'
                )

            summary_path = Path(week_notes[0]['path']).parent / f"semanal-{week_key}.md"
            summary_fm = {
                'tags': ['consolidado', 'semanal'],
                'created': datetime.now().strftime('%Y-%m-%d'),
                'type': 'session',
                'agent': 'refinement-engine',
                'project': week_notes[0]['frontmatter'].get('project', ''),
                'sync_status': 'pending',
                'refined': True
            }
            summary_path.write_text(
                write_frontmatter(summary_fm) + summary_content,
                encoding='utf-8'
            )
            print(f"  Consolidado: semanal-{week_key}.md ({len(week_notes)} notas)")
        else:
            consolidated.extend(week_notes)

    return [n for n in notes if n['category'] != 'diario'] + consolidated

def run_refinement():
    config = load_config()
    min_age = config['refinement']['min_note_age_days']

    print(f"[{datetime.now().isoformat()}] Iniciando refinamiento...")

    for project in config['projects']:
        if not project.get('enabled', True):
            continue

        print(f"\nProyecto: {project['name']}")
        notes = get_all_notes(project['path'])
        to_refine = [n for n in notes if should_refine(n, min_age)]
        print(f"  Notas a evaluar: {len(to_refine)}")

        low_relevance = []
        high_relevance = []

        for note in to_refine:
            score = calculate_relevance_score(note)
            if score < config['refinement']['consolidate_threshold']:
                low_relevance.append(note)
            else:
                high_relevance.append(note)

        print(f"  Baja relevancia: {len(low_relevance)}")
        print(f"  Alta relevancia: {len(high_relevance)}")

        remaining = consolidate_daily_notes([n for n in notes if n['category'] == 'diario'])

        for note in low_relevance:
            note['frontmatter']['refined'] = True
            note['frontmatter']['refined_at'] = datetime.now().isoformat()
            note['frontmatter']['relevance_score'] = calculate_relevance_score(note)
            Path(note['path']).write_text(
                write_frontmatter(note['frontmatter']) + note['body'],
                encoding='utf-8'
            )

    print(f"\n[{datetime.now().isoformat()}] Refinamiento completado.")

if __name__ == '__main__':
    run_refinement()
