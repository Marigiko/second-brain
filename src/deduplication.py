#!/usr/bin/env python3
"""
Deduplication Engine - Detecta y mergea notas similares.
Si dos aprendizajes tratan el mismo tema pero en contextos diferentes,
se guardan ambos con cross-references.
"""

import os
import sys
import json
import yaml
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

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

def extract_tags(frontmatter):
    return set(frontmatter.get('tags', []))

def jaccard_similarity(set_a, set_b):
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0

def find_similar_notes(notes, threshold=0.5):
    similar_pairs = []
    aprendizajes = [n for n in notes if n['category'] == 'aprendizajes']

    for i, note_a in enumerate(aprendizajes):
        for note_b in aprendizajes[i+1:]:
            tags_a = extract_tags(note_a['frontmatter'])
            tags_b = extract_tags(note_b['frontmatter'])
            similarity = jaccard_similarity(tags_a, tags_b)
            if similarity >= threshold:
                similar_pairs.append((note_a, note_b, similarity))

    return similar_pairs

def merge_or_cross_reference(note_a, note_b, similarity):
    if note_a['frontmatter'].get('project') == note_b['frontmatter'].get('project'):
        return 'merge'
    return 'cross-reference'

def add_cross_reference(note, other_note):
    ref_text = f"\n\n**Ver tambien:** {other_note['filename'].replace('.md', '')} (proyecto: {other_note['frontmatter'].get('project', 'N/A')})"

    if 'cross_references' not in note['frontmatter']:
        note['frontmatter']['cross_references'] = []

    note['frontmatter']['cross_references'].append({
        'file': other_note['filename'],
        'project': other_note['frontmatter'].get('project', '')
    })

    if ref_text not in note['body']:
        note['body'] += ref_text

    note['frontmatter']['sync_status'] = 'pending'
    note['frontmatter']['refined'] = True

def run_deduplication():
    config = load_config()

    print(f"[{datetime.now().isoformat()}] Iniciando deduplicacion...")

    all_notes = []
    for project in config['projects']:
        if not project.get('enabled', True):
            continue

        sb_dir = Path(project['path']) / SECOND_BRAIN_DIR
        if not sb_dir.exists():
            continue

        categories = ['decisiones', 'aprendizajes', 'convenciones', 'arquitectura']
        for category in categories:
            cat_dir = sb_dir / category
            if not cat_dir.exists():
                continue

            for md_file in cat_dir.glob('*.md'):
                content = md_file.read_text(encoding='utf-8')
                fm, body = read_frontmatter(content)

                all_notes.append({
                    'path': str(md_file),
                    'category': category,
                    'filename': md_file.name,
                    'frontmatter': fm,
                    'body': body,
                    'content': content
                })

    similar_pairs = find_similar_notes(all_notes)
    print(f"  Pares similares encontrados: {len(similar_pairs)}")

    for note_a, note_b, sim in similar_pairs:
        action = merge_or_cross_reference(note_a, note_b, sim)

        if action == 'cross-reference':
            add_cross_reference(note_a, note_b)
            add_cross_reference(note_b, note_a)

            Path(note_a['path']).write_text(
                write_frontmatter(note_a['frontmatter']) + note_a['body'],
                encoding='utf-8'
            )
            Path(note_b['path']).write_text(
                write_frontmatter(note_b['frontmatter']) + note_b['body'],
                encoding='utf-8'
            )

            print(f"  Cross-ref: {note_a['filename']} <-> {note_b['filename']} (sim={sim:.2f})")

    print(f"[{datetime.now().isoformat()}] Deduplicacion completada.")

if __name__ == '__main__':
    run_deduplication()
