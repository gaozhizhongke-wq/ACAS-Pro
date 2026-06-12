#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix encoding issues in dashboard_logic.py"""


# Read the file
with open('src/acas_pro/ui/logic/dashboard_logic.py.bak', 'rb') as f:
    content = f.read()

# Decode with replacement to see the damage
text = content.decode('utf-8', errors='replace')

# Define the fixes
fixes = {
    106: 'title="总营收",',
    108: 'subtitle=f"较上月{self._format_trend(revenue_trend)}",',
    120: 'subtitle=f"较上月{self._format_trend(orders_trend)}",',
    143: 'alert_text = f"{critical}个紧急 {high}个高"',
    146: 'alert_text = "无风险"',
    164: 'QuickAction(id="inventory", label="库存检查", icon="📦"),',
    223: 'return f"¥{value/10000:.1f}万"',
    230: 'return f"{value/10000:.1f}万"',
    236: 'arrow = "↑" if percent > 0 else "↓" if percent < 0 else "→"'
}

# Split into lines
lines = text.split('\n')

# Apply fixes
fixed_count = 0
for line_num, fix in fixes.items():
    idx = line_num - 1  # 0-indexed
    if idx < len(lines):
        lines[idx] = fix
        fixed_count += 1

# Reconstruct the text
fixed_text = '\n'.join(lines)

# Write the fixed file
with open('src/acas_pro/ui/logic/dashboard_logic.py', 'w', encoding='utf-8') as f:
    f.write(fixed_text)

print(f'Fixed {fixed_count} lines in dashboard_logic.py')

# Verify the file can be parsed
try:
    compile(fixed_text, 'dashboard_logic.py', 'exec')
    print('Syntax verification: PASSED')
except SyntaxError as e:
    print(f'Syntax error: {e}')
