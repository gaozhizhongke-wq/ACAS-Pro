import os
import re

# Files that import config from core.config and use config()
files_to_fix = [
    'src/acas_pro/ads/ad_manager.py',
    'src/acas_pro/ads/audience_targeting.py',
    'src/acas_pro/avatar/avatar_engine.py',
    'src/acas_pro/avatar/lip_sync.py',
    'src/acas_pro/avatar/scene_adapter.py',
    'src/acas_pro/llm/tools.py',
    'src/acas_pro/web/api_spec.py',
    'src/acas_pro/web/health.py',
    'src/acas_pro/web/__init__.py',
    'src/acas_pro/web/routes/auth.py',
    'src/acas_pro/web/routes/dashboard_stats.py',
    'src/acas_pro/web/routes/llm.py',
]

for path in files_to_fix:
    if not os.path.exists(path):
        print(f'SKIP (not found): {path}')
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace config() followed by .attribute with config.attribute
    # This regex matches config() followed by a dot and an identifier
    content = re.sub(r'config\(\)(\.[a-zA-Z_][a-zA-Z0-9_]*)', r'config\1', content)
    
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'FIXED: {path}')
    else:
        print(f'NO CHANGE: {path}')

print('\nDone!')
