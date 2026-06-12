from acas_pro.ui.logic.settings_logic import SettingsLogic, SettingItem


class TestSettingItem:
    def test_create_item(self):
        item = SettingItem(
            key='theme',
            label='Theme',
            value='dark',
            type='select',
            options=['light', 'dark'],
            description='UI theme'
        )
        assert item.key == 'theme'
        assert item.value == 'dark'
        assert item.type == 'select'

    def test_defaults(self):
        item = SettingItem(key='x', label='X', value=1, type='number')
        assert item.options is None
        assert item.description == ''


class TestSettingsLogic:
    def test_get_setting_exists(self):
        logic = SettingsLogic()
        item = SettingItem(key='theme', label='Theme', value='dark', type='select')
        logic._settings['theme'] = item
        result = logic.get_setting('theme')
        assert result is item

    def test_get_setting_missing(self):
        logic = SettingsLogic()
        assert logic.get_setting('nonexistent') is None

    def test_set_setting_exists(self):
        logic = SettingsLogic()
        item = SettingItem(key='theme', label='Theme', value='light', type='select')
        logic._settings['theme'] = item
        assert logic.set_setting('theme', 'dark') is True
        assert logic._settings['theme'].value == 'dark'

    def test_set_setting_missing(self):
        logic = SettingsLogic()
        assert logic.set_setting('missing', 'value') is False

    def test_get_all_settings(self):
        logic = SettingsLogic()
        logic._settings['a'] = SettingItem(key='a', label='A', value=1, type='number')
        logic._settings['b'] = SettingItem(key='b', label='B', value=2, type='number')
        assert len(logic.get_all_settings()) == 2

    def test_export_settings(self):
        logic = SettingsLogic()
        logic._settings['theme'] = SettingItem(key='theme', label='Theme', value='dark', type='select')
        logic._settings['volume'] = SettingItem(key='volume', label='Volume', value=80, type='number')
        data = logic.export_settings()
        assert data == {'theme': 'dark', 'volume': 80}

    def test_import_settings(self):
        logic = SettingsLogic()
        logic._settings['theme'] = SettingItem(key='theme', label='Theme', value='light', type='select')
        logic._settings['volume'] = SettingItem(key='volume', label='Volume', value=50, type='number')
        assert logic.import_settings({'theme': 'dark', 'volume': 80}) is True
        assert logic._settings['theme'].value == 'dark'
        assert logic._settings['volume'].value == 80

    def test_import_settings_ignores_missing_key(self):
        logic = SettingsLogic()
        # import_settings iterates all keys; for missing keys set_setting returns False
        # but import_settings itself returns True regardless
        result = logic.import_settings({'nonexistent': 'value'})
        assert result is True  # function does not fail on missing keys
