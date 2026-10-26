import pilot_backend as p


def create_assignment():
    return p.dispatch('POST', '/api/pilot/assignments', {
        'title': 'Fictional test assignment', 'instructions': 'Assess evidence only.',
        'rubric': {'name': 'Test rubric', 'criteria': [
            {'id': 'methods', 'name': 'Methods', 'maximum_points': 30},
            {'id': 'results', 'name': 'Results', 'maximum_points': 30},
            {'id': 'discussion', 'name': 'Discussion', 'maximum_points': 40}]}}, None)['id']


def analysis_output():
    return {'summary': 'A fictional report with insufficient replication.',
            'outline': [{'title': 'Methods', 'paragraph_ids': ['p1', 'p2']}],
            'claims': [{'title': 'Growth increased', 'paragraph_ids': ['p4']}],
            'findings': [
                {'title': 'Replication', 'paragraph_ids': ['p2'], 'criterion_id': 'methods',
                 'kind': 'issue', 'quote': 'Each measurement was performed once',
                 'rationale': 'Single measurements cannot estimate variation.', 'feedback': 'Add replication.'},
                {'title': 'Measured growth', 'paragraph_ids': ['p4'], 'criterion_id': 'results',
                 'kind': 'strength', 'quote': 'OD600 increased from 0.08 to 0.72',
                 'rationale': 'The report states numerical results.', 'feedback': 'Clear quantitative results.'}]}
