from acas_pro.ui.logic.settings_logic import SettingsLogic, SettingItem


class TestSettingItem:
    """Test SettingItem dataclass"""
    
    def test_item_creation(self):
        """Test creating a setting item"""
        item = SettingItem(
            key="theme",
            label="Theme",
            value="dark",
            type="select",
            options=["light", "dark"],
            description="UI theme"
        )
        
        assert item.key == "theme"
        assert item.label == "Theme"
        assert item.value == "dark"
        assert item.type == "select"
        assert item.options == ["light", "dark"]
        assert item.description == "UI theme"

    def test_item_defaults(self):
        """Test setting item defaults"""
        item = SettingItem(
            key="debug",
            label="Debug Mode",
            value=False,
            type="boolean"
        )
        
        assert item.options is None
        assert item.description == ""


class TestSettingsLogicInit:
    """Test SettingsLogic initialization"""
    
    def test_init(self):
        """Test initialization"""
        logic = SettingsLogic()
        
        assert logic._settings == {}


class TestGetSetting:
    """Test getting settings"""
    
    def test_get_existing(self):
        """Test getting existing setting"""
        logic = SettingsLogic()
        logic._settings["theme"] = SettingItem(
            key="theme", label="Theme", value="dark", type="select"
        )
        
        result = logic.get_setting("theme")
        
        assert result is not None
        assert result.value == "dark"

    def test_get_nonexistent(self):
        """Test getting non-existent setting"""
        logic = SettingsLogic()
        
        result = logic.get_setting("nonexistent")
        
        assert result is None


class TestSetSetting:
    """Test setting values"""
    
    def test_set_existing(self):
        """Test setting existing value"""
        logic = SettingsLogic()
        logic._settings["theme"] = SettingItem(
            key="theme", label="Theme", value="dark", type="select"
        )
        
        result = logic.set_setting("theme", "light")
        
        assert result is True
        assert logic._settings["theme"].value == "light"

    def test_set_nonexistent(self):
        """Test setting non-existent value"""
        logic = SettingsLogic()
        
        result = logic.set_setting("nonexistent", "value")
        
        assert result is False

    def test_set_different_types(self):
        """Test setting different types"""
        logic = SettingsLogic()
        logic._settings["debug"] = SettingItem(
            key="debug", label="Debug", value=False, type="boolean"
        )
        logic._settings["count"] = SettingItem(
            key="count", label="Count", value=0, type="number"
        )
        
        logic.set_setting("debug", True)
        logic.set_setting("count", 42)
        
        assert logic._settings["debug"].value is True
        assert logic._settings["count"].value == 42


class TestGetAllSettings:
    """Test getting all settings"""
    
    def test_empty(self):
        """Test getting all when empty"""
        logic = SettingsLogic()
        
        result = logic.get_all_settings()
        
        assert result == []

    def test_multiple(self):
        """Test getting multiple settings"""
        logic = SettingsLogic()
        logic._settings["a"] = SettingItem(key="a", label="A", value=1, type="number")
        logic._settings["b"] = SettingItem(key="b", label="B", value="test", type="string")
        
        result = logic.get_all_settings()
        
        assert len(result) == 2
        assert all(isinstance(item, SettingItem) for item in result)


class TestExportSettings:
    """Test exporting settings"""
    
    def test_empty_export(self):
        """Test exporting empty settings"""
        logic = SettingsLogic()
        
        result = logic.export_settings()
        
        assert result == {}

    def test_export_values(self):
        """Test exporting values"""
        logic = SettingsLogic()
        logic._settings["theme"] = SettingItem(
            key="theme", label="Theme", value="dark", type="select"
        )
        logic._settings["debug"] = SettingItem(
            key="debug", label="Debug", value=True, type="boolean"
        )
        
        result = logic.export_settings()
        
        assert result == {"theme": "dark", "debug": True}


class TestImportSettings:
    """Test importing settings"""
    
    def test_import_empty(self):
        """Test importing empty data"""
        logic = SettingsLogic()
        
        result = logic.import_settings({})
        
        assert result is True

    def test_import_values(self):
        """Test importing values"""
        logic = SettingsLogic()
        logic._settings["theme"] = SettingItem(
            key="theme", label="Theme", value="dark", type="select"
        )
        
        result = logic.import_settings({"theme": "light"})
        
        assert result is True
        assert logic._settings["theme"].value == "light"

    def test_import_new_keys(self):
        """Test importing new keys"""
        logic = SettingsLogic()
        logic._settings["existing"] = SettingItem(
            key="existing", label="Existing", value="old", type="string"
        )
        
        # Import should only update existing keys
        result = logic.import_settings({"existing": "new", "new_key": "value"})
        
        assert result is True
        assert logic._settings["existing"].value == "new"
        # new_key should not be added since it doesn't exist
        assert "new_key" not in logic._settings
