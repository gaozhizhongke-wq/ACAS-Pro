#!/usr/bin/env python3
"""Inspect top non-UI modules for test writing"""
import ast, sys, os

targets = [
    'src/acas_pro/core/security.py',
    'src/acas_pro/advanced_analytics/smart_decider.py',
    'src/acas_pro/llm/agent_engine.py',
    'src/acas_pro/avatar/scene_adapter.py',
    'src/acas_pro/alert/notifier.py',
    'src/acas_pro/publisher/publish_manager.py',
    'src/acas_pro/collectors/rss_collector.py',
    'src/acas_pro/core/logging_v2.py',
    'src/acas_pro/avatar/lip_sync.py',
    'src/acas_pro/video/video_maker.py',
    'src/acas_pro/llm/tools.py',
    'src/acas_pro/core/security_v2.py',
    'src/acas_pro/llm/llm_client.py',
    'src/acas_pro/ui/logic/analytics_logic.py',
    'src/acas_pro/ml/timesfm_engine.py',
    'src/acas_pro/ml/inventory_optimizer.py',
    'src/acas_pro/web/routes/llm.py',
    'src/acas_pro/update/updater.py',
]

for path in targets:
    if not os.path.exists(path):
        print(f"MISSING: {path}")
        continue
    with open(path, encoding='utf-8-sig') as f:
        content = f.read()
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"PARSE ERROR: {path}: {e}")
        continue
    
    print(f"\n{'='*60}")
    print(f"{path}")
    print(f"{'='*60}")
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in item.args.args if a.arg != 'self']
                    methods.append(f"  L{item.lineno} {item.name}({', '.join(args)})")
            print(f"L{node.lineno} class {node.name} ({len(methods)} methods)")
            for m in methods:
                print(m)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            print(f"L{node.lineno} def {node.name}({', '.join(args)})")
