import sys
from unittest.mock import patch

# Simulate: import first
from acas_pro.i18n.translator import t, translator as orig_translator

# Store original module ref
mod1 = sys.modules['acas_pro.i18n.translator']
trans1 = mod1.translator
print(f'Before clear: module id={id(mod1)}, translator id={id(trans1)}')

# Simulate _clear
del sys.modules['acas_pro.i18n.translator']

# Simulate reimport
import acas_pro.i18n.translator as mod2
trans2 = mod2.translator
print(f'After reimport: module id={id(mod2)}, translator id={id(trans2)}')
print(f'Same module? {mod1 is mod2}')
print(f'Same translator? {trans1 is trans2}')

# Now try patch on the NEW module
with patch.object(mod2, 'translator') as mock_t:
    mock_t.t.return_value = 'MOCKED'
    print(f'Patched. mod2.translator is mock? {mod2.translator is mock_t}')
    # What does the OLD t function reference?
    result = t('hello')
    print(f't("hello") returned: {repr(result)}')
    print(f'Old t still references old module? {t.__module__}')
