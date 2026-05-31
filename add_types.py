import os
import re

def add_type_annotations(filepath):
    """Add return type annotations to functions without them."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Pattern: def func_name(...) -> None:  (already typed)
    # Pattern: def func_name(...):  (needs typing)
    
    # Find functions without return type annotation
    pattern = r'^(\s*)def\s+(\w+)\s*\(([^)]*)\)\s*:(?!\s*->)'
    
    def replace_func(match):
        indent = match.group(1)
        func_name = match.group(2)
        params = match.group(3)
        
        # Skip if already has type annotation in params or is a property
        if '->' in match.group(0):
            return match.group(0)
        
        # Determine return type based on function name patterns
        if func_name.startswith('get_') or func_name.startswith('find_') or func_name.startswith('fetch_'):
            return_type = 'Any'
        elif func_name.startswith('is_') or func_name.startswith('has_'):
            return_type = 'bool'
        elif func_name.startswith('create_') or func_name.startswith('add_'):
            return_type = 'Any'
        elif func_name.startswith('update_') or func_name.startswith('delete_'):
            return_type = 'bool'
        elif func_name.startswith('check_') or func_name.startswith('validate_'):
            return_type = 'bool'
        elif func_name.startswith('load_') or func_name.startswith('save_'):
            return_type = 'Any'
        elif func_name.startswith('init') or func_name.startswith('setup'):
            return_type = 'None'
        elif func_name.startswith('render') or func_name.startswith('generate'):
            return_type = 'str'
        else:
            return_type = 'Any'
        
        return f'{indent}def {func_name}({params}) -> {return_type}:'
    
    new_content = re.sub(pattern, replace_func, content, flags=re.MULTILINE)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

# Process key modules
modules = [
    'src/acas_pro/web/health.py',
    'src/acas_pro/web/routes/dashboard.py',
    'src/acas_pro/web/routes/llm.py',
    'src/acas_pro/web/middleware.py',
]

modified = 0
for module in modules:
    path = os.path.join('C:/Users/HUAWEI/.qclaw/workspace-hermes/ACAS-Pro', module)
    if os.path.exists(path):
        if add_type_annotations(path):
            print(f'Modified: {module}')
            modified += 1
        else:
            print(f'No changes: {module}')
    else:
        print(f'Not found: {module}')

print(f'\nTotal modified: {modified}')
