import json
with open('coverage.json','r') as f:
    data = json.load(f)
targets = ['core/config.py','core/database.py','llm/llm_client.py','content/script_generator.py','blockchain/wallet_manager.py','collectors/rss_collector.py','video/video_maker.py','avatar/lip_sync.py','ml/inventory_optimizer.py','llm/tools.py','core/security.py','publisher/publish_manager.py','alert/notifier.py','advanced_analytics/smart_decider.py','services/oauth/oauth_service.py','llm/agent_engine.py']
for path, info in data['files'].items():
    for t in targets:
        if t.replace('/', '\\') in path and 'acas_pro' in path:
            s = info['summary']
            ml = info.get('missing_lines_list',[])
            miss = s['missing_lines']
            pct = s['percent_covered']
            print(path + ': ' + str(miss) + ' missing (' + str(int(pct)) + '%)')
            print('  Lines: ' + str(ml[:20]))
