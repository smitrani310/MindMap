"""Theme definitions for the mind map application."""

# UI Constants
PRIMARY_NODE_BORDER = 2
RGBA_ALPHA = 0.7

# Node size based on urgency
URGENCY_SIZE = {
    'high': 25,
    'medium': 20,
    'low': 15
}

# Tag definitions with defaults
TAGS = {
    'work': {'color': '#2196F3', 'description': 'Work-related items'},
    'personal': {'color': '#9C27B0', 'description': 'Personal items'},
    'idea': {'color': '#00BCD4', 'description': 'Creative ideas'},
    'task': {'color': '#FF9800', 'description': 'Tasks to be completed'},
    'note': {'color': '#607D8B', 'description': 'General notes'},
    'important': {'color': '#F44336', 'description': 'Important items'},
    'question': {'color': '#8BC34A', 'description': 'Questions to explore'},
    'research': {'color': '#3F51B5', 'description': 'Research topics'}
}

# Theme definitions
THEMES = {
    'default': {
        'background': '#FFFFFF',
        'text': '#000000',
        'node': '#EEEEEE',
        'urgency_colors': {
            'high': '#FF5252',
            'medium': '#FFC107',
            'low': '#4CAF50'
        },
        'edge_colors': {
            'default': '#999999',
            'strong': '#444444',
            'weak': '#CCCCCC',
            'dependency': '#FF0000',
            'relation': '#0000FF',
            'influence': '#00FF00'
        }
    },
    'dark': {
        'background': '#2E3440',
        'text': '#D8DEE9',
        'node': '#3B4252',
        'urgency_colors': {
            'high': '#BF616A',
            'medium': '#EBCB8B',
            'low': '#A3BE8C'
        },
        'edge_colors': {
            'default': '#81A1C1',
            'strong': '#D8DEE9',
            'weak': '#4C566A',
            'dependency': '#BF616A',
            'relation': '#81A1C1',
            'influence': '#A3BE8C'
        }
    },
    'solarized': {
        'background': '#FDF6E3',
        'text': '#657B83',
        'node': '#EEE8D5',
        'urgency_colors': {
            'high': '#DC322F',
            'medium': '#CB4B16',
            'low': '#859900'
        },
        'edge_colors': {
            'default': '#93A1A1',
            'strong': '#657B83',
            'weak': '#EEE8D5',
            'dependency': '#DC322F',
            'relation': '#268BD2',
            'influence': '#859900'
        }
    },
    'midnight': {
        'background': '#121212',
        'text': '#FFFFFF',
        'node': '#1E1E1E',
        'urgency_colors': {
            'high': '#CF6679',
            'medium': '#FFAB40',
            'low': '#03DAC6'
        },
        'edge_colors': {
            'default': '#BB86FC',
            'strong': '#FFFFFF',
            'weak': '#3B3B3B',
            'dependency': '#CF6679',
            'relation': '#BB86FC',
            'influence': '#03DAC6'
        }
    }
} 