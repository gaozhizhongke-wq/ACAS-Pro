#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

content = open('web_app.py', 'r', encoding='utf-8').read()

# Check for remaining XSS issues - template literals in innerHTML
issues = []
pattern = r'tbody\.innerHTML = `[^`]*\$\{[^}]+\}[^`]*`'
matches = re.findall(pattern, content)
for m in matches:
    issues.append(m[:120])

if issues:
    print('Remaining template literal issues:')
    for i in issues:
        print(' -', i)
else:
    print('No remaining template literal issues in tbody.innerHTML')

# Check chatWithAI
idx = content.find('async function chatWithAI')
if idx >= 0:
    snippet = content[idx:idx+600]
    print('\nchatWithAI return:')
    print(snippet[snippet.find('return'):snippet.find('return')+100])

# Check escapeHtml exists
if 'function escapeHtml(str)' in content:
    print('\nescapeHtml function: FOUND')
else:
    print('\nescapeHtml function: NOT FOUND')

# Check old escapeHtml removed
if 'document.createElement' in content and 'div.textContent' in content:
    print('Old escapeHtml: STILL PRESENT (should be removed)')
else:
    print('Old escapeHtml: removed')
print('\nFile length:', len(content))