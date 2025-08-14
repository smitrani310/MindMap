#!/usr/bin/env python3
"""Fix Unicode characters in test files for Windows compatibility."""

import re

def fix_unicode_in_file(filename):
    """Fix Unicode characters in a file."""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace common Unicode characters
    replacements = {
        '✓': '-',
        '✅': '[OK]',
        '❌': '[ERROR]',
        '🧪': '[TEST]',
        '🎉': '[SUCCESS]',
        '🚀': '[START]',
        '📁': '[FOLDER]',
        '🏗️': '[ARCH]',
        '🎯': '[TARGET]',
        '👋': '[BYE]',
        '📱': '[MOBILE]',
        '🔗': '[LINK]',
    }
    
    for unicode_char, replacement in replacements.items():
        content = content.replace(unicode_char, replacement)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed Unicode characters in {filename}")

if __name__ == "__main__":
    fix_unicode_in_file("test_new_main.py")
    fix_unicode_in_file("run_new_app.py")
    print("Unicode fix complete!")