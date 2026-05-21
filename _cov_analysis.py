import subprocess, re, os, sys

env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'
r = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/unit/', '--cov=src/acas_pro', '--cov-report=term-missing', '--tb=no', '-q'],
    capture_output=True, env=env, cwd=r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro'
)
text = r.stdout.decode('utf-8', errors='replace')
ui_t = ui_m = nu_t = nu_m = 0
for line in text.strip().split('\n'):
    if not line.startswith('src'):
        continue
    m = re.search(r'(\d+)\s+(\d+)\s+(\d+)%', line)
    if not m:
        continue
    total, miss, pct = int(m.group(1)), int(m.group(2)), int(m.group(3))
    is_ui = os.sep + 'ui' + os.sep in line or '\\ui\\' in line
    if is_ui:
        ui_t += total
        ui_m += miss
    else:
        nu_t += total
        nu_m += miss

nu_cov = nu_t - nu_m
ui_cov = ui_t - ui_m
print(f'Non-UI: {nu_cov}/{nu_t} = {nu_cov * 100 // max(nu_t, 1)}%')
print(f'UI:     {ui_cov}/{ui_t} = {ui_cov * 100 // max(ui_t, 1)}%')
print(f'Combined: {nu_cov + ui_cov}/{nu_t + ui_t} = {(nu_cov + ui_cov) * 100 // max(nu_t + ui_t, 1)}%')
