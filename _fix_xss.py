#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix XSS vulnerabilities in web_app.py"""

import re

with open('web_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# 1. Add escapeHtml function before "// ── State ──"
old_state = '        // ── State ──\n        let authToken'
new_state = '''        function escapeHtml(str) {
            if (str == null) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        // ── State ──
        let authToken'''
content = content.replace(old_state, new_state)

# 2. chatWithAI return values with escapeHtml
content = content.replace(
    "return data.success ? data.content : '❌ ' + (data.error || '请求失败');",
    "return data.success ? escapeHtml(data.content) : '❌ ' + escapeHtml(data.error || '请求失败');"
)

# 3. Network error with escapeHtml
content = content.replace(
    "'❌ 网络错误: ' + e.message;",
    "'❌ 网络错误: ' + escapeHtml(e.message);"
)

# 4. Replace .replace(/</g,'&lt;').replace(/>/g,'&gt;') with escapeHtml(res)
content = content.replace(
    "res.replace(/</g,'&lt;').replace(/>/g,'&gt;')",
    "escapeHtml(res)"
)

# 5. Replace template literals with explicit string concat for all innerHTML
# Festival: f.name, f.festival_type, f.themes need escaping
content = content.replace(
    "`${f.name}`",
    "' + escapeHtml(f.name) + '"
)
content = content.replace(
    "`${date}`",
    "' + date + '"
)
content = content.replace(
    "`${f.festival_type || '-'}`",
    "' + escapeHtml(f.festival_type || '-') + '"
)
content = content.replace(
    "`${themes}${themes?'...':''}`",
    "' + themes + (themes?'...':'') + '"
)

# 6. Fix forecast: r.date, r.platform template literals
# The forecast code uses `${r.date}` etc - need to replace
content = content.replace(
    "`${r.date || '-'}`",
    "' + escapeHtml(r.date || '-') + '"
)
content = content.replace(
    "`${r.platform || '-'}`",
    "' + escapeHtml(r.platform || '-') + '"
)
content = content.replace(
    "`¥${rev}`",
    "'¥' + rev"
)
content = content.replace(
    "`${r.orders || 0}`",
    "' + (r.orders || 0) + '"
)
content = content.replace(
    "`${(r.views || 0).toLocaleString()}`",
    "' + (r.views || 0).toLocaleString()"
)

# 7. Fix inventory: p.name, p.category, p.status
content = content.replace(
    "`${p.name || '-'}`",
    "' + escapeHtml(p.name || '-') + '"
)
content = content.replace(
    "`${p.category || '-'}`",
    "' + escapeHtml(p.category || '-') + '"
)
content = content.replace(
    "`${p.status || '-'}`",
    "' + escapeHtml(p.status || '-') + '"
)
content = content.replace(
    "`${(p.price || 0).toLocaleString()}`",
    "' + (p.price || 0).toLocaleString()"
)
content = content.replace(
    "`${p.stock_quantity || 0}`",
    "' + (p.stock_quantity || 0)"
)
content = content.replace(
    "`${p.reorder_point || 0}`",
    "' + (p.reorder_point || 0)"
)
content = content.replace(
    "`${p.deficit || 0}`",
    "' + (p.deficit || 0)"
)

# 8. Fix accounts: a.platform, a.account_name, a.status
content = content.replace(
    "`${a.platform || '-'}`",
    "' + escapeHtml(a.platform || '-') + '"
)
content = content.replace(
    "`${a.account_name || '-'}`",
    "' + escapeHtml(a.account_name || '-') + '"
)
content = content.replace(
    "`${(a.status || '-')}`",
    "' + escapeHtml(a.status || '-') + '"
)
content = content.replace(
    "`${(a.followers || 0).toLocaleString()}`",
    "' + (a.followers || 0).toLocaleString()"
)
content = content.replace(
    "`${a.content_count || 0}`",
    "' + (a.content_count || 0)"
)
content = content.replace(
    "`${(a.total_views || 0).toLocaleString()}`",
    "' + (a.total_views || 0).toLocaleString()"
)

# 9. Fix `rows.length` template literals
content = content.replace(
    "`${rows.length}`",
    "' + rows.length + '"
)

# 10. Fix data.products.length template literal
content = content.replace(
    "(' + data.products.length + ' 项)",
    "(' + escapeHtml(String(data.products.length)) + ' 项)"
)

# 11. Replace '加载失败: ' + e.message (5 occurrences)
content = content.replace(
    "'加载失败: ' + e.message + '</td></tr>';",
    "'加载失败: ' + escapeHtml(e.message) + '</td></tr>';"
)

# 12. Fix HTML entities from star encoding
content = content.replace('&#9733;', '&#9733;')  # keep entities for stars

# 13. Remove old escapeHtml at bottom
old_bottom = '''        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

    </script>'''
new_bottom = '''    </script>'''
content = content.replace(old_bottom, new_bottom)

with open('web_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Done. Changed {len(content) - len(original)} chars')