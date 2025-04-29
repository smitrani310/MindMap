# Theme and tag definitions for MindMap

RGBA_ALPHA = 0.5

THEMES = {
    'default': {
        'background': '#FFFFFF',
        'urgency_colors': {'high': '#e63946', 'medium': '#f4a261', 'low': '#2a9d8f'},
        'edge_colors': {'default': '#848484', 'supports': '#2a9d8f', 'contradicts': '#e63946', 'relates': '#f4a261'}
    },
    'dark': {
        'background': '#2E3440',
        'urgency_colors': {'high': '#BF616A', 'medium': '#EBCB8B', 'low': '#A3BE8C'},
        'edge_colors': {'default': '#D8DEE9', 'supports': '#A3BE8C', 'contradicts': '#BF616A', 'relates': '#EBCB8B'}
    },
    'pastel': {
        'background': '#F8F9FA',
        'urgency_colors': {'high': '#FF9AA2', 'medium': '#FFB347', 'low': '#98DDCA'},
        'edge_colors': {'default': '#9BA4B4', 'supports': '#98DDCA', 'contradicts': '#FF9AA2', 'relates': '#FFB347'}
    },
    'vibrant': {
        'background': '#FFFFFF',
        'urgency_colors': {'high': '#FF1E56', 'medium': '#FFAC41', 'low': '#16C79A'},
        'edge_colors': {'default': '#666666', 'supports': '#16C79A', 'contradicts': '#FF1E56', 'relates': '#FFAC41'}
    }
}

TAGS = {
    'idea': '#4361EE',
    'task': '#3A0CA3',
    'question': '#7209B7',
    'project': '#F72585',
    'note': '#4CC9F0',
    'research': '#560BAD',
    'personal': '#F3722C',
    'work': '#F8961E'
}

# Make urgency size differences more pronounced
URGENCY_SIZE = {'high': 400, 'medium': 200, 'low': 100}
PRIMARY_NODE_BORDER = 4 