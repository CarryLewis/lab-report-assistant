"""Versioned writing guidance and original, genre-scoped wording references."""
import copy
import json

from app_paths import ROOT


def catalog():
    return json.loads((ROOT / 'corpus' / 'writing_profiles.json').read_text(encoding='utf-8'))


def for_type(assignment_type):
    label = assignment_type.strip().casefold()
    profiles = catalog()['profiles']
    selected = next((p for p in profiles if label in
                     [x.casefold() for x in [p['name'], *p['aliases']]]), None)
    # Unknown/custom labels must never silently inherit experimental requirements.
    return copy.deepcopy(selected or next(p for p in profiles if p['id'] == 'general_writing'))


def review_context(assignment):
    profile = assignment.get('writing_profile') or for_type(assignment.get('assignment_type', '实验报告'))
    names = {c['name'] for c in assignment['rubric']['criteria']}
    return {
        'profile_id': profile['id'], 'profile_version': profile['version'],
        'name': profile['name'], 'focus': profile['focus'], 'cautions': profile['cautions'],
        'wording_reference_only': [e for e in profile['feedback_examples'] if e['criterion_name'] in names],
    }
