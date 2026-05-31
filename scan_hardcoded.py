import os, re

real_issues = []

# True hardcoded patterns: actual secret values assigned, not variable declarations
patterns = [
    # Actual API keys/secrets assigned as string literals (not variable declarations)
    re.compile(r'=\s*[\'"]+(sk-|pk-|Bearer\s+)[A-Za-z0-9_\-]{20,}[\'"]+'),
    re.compile(r'=\s*[\'"][A-Za-z0-9+/]{40,}[\'"]+\s*$'),
    re.compile(r'(api_key|apikey|secret_key|password|passwd)\s*=\s*[\'"][^\'"\s]{8,}[\'"]'),
]

false_positives = [
    'os.environ', 'getenv', 'config(', 'getattr', 'decrypt_data',
    'encrypt_data', 'secrets.', 'token_hex', 'token_urlsafe', 'token_bytes',
    'field(default', 'Optional', '#', 'PlaceholderText', 'setPlaceholderText',
    'self.', 'access_token=access_token', 'self.app_secret', 'self.access_token',
]

for root, dirs, files in os.walk('src'):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                for lineno, line in enumerate(fh, 1):
                    line_s = line.strip()
                    if not line_s or line_s.startswith('#'):
                        continue
                    for pat in patterns:
                        if pat.search(line):
                            if any(fp in line for fp in false_positives):
                                continue
                            real_issues.append((fpath, lineno, line.rstrip()))
        except:
            pass

print(f'Real hardcoded credential issues: {len(real_issues)}')
for fpath, lineno, line in real_issues[:30]:
    rel = os.path.relpath(fpath)
    print(f'  {rel}:{lineno}: {line[:130]}')
