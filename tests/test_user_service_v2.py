"""Test User Service v2"""
import pytest
import tempfile
import os


class TestUserServiceV2:
    """Test user service v2"""
    
    def test_user_service_init(self):
        from acas_pro.services.user_service_v2 import UserService
        from acas_pro.core.config_v2 import AppConfig
        from acas_pro.core.database_v2 import DatabaseManager
        
        # Use temp database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        config = AppConfig()
        config.database.path = db_path
        config.database.type = 'sqlite'
        
        db = DatabaseManager(config.database)
        service = UserService(config=config, db=db)
        assert service is not None
        
        # Cleanup
        db.close()
        os.unlink(db_path)
    
    def test_register_user(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        success, result = service.register(
            account="testuser",
            password="ValidPass123!",
            email="test@example.com",
            nickname="Test User"
        )
        assert success
        assert len(result) > 0  # user_id
    
    def test_register_duplicate_account(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        # Register first user
        service.register(account="dupuser", password="ValidPass123!")
        
        # Try duplicate
        success, msg = service.register(account="dupuser", password="ValidPass123!")
        assert not success
        assert "already exists" in msg
    
    def test_register_weak_password(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        success, msg = service.register(account="weakuser", password="short")
        assert not success
        assert "at least" in msg
    
    def test_login_success(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        # Register
        service.register(account="loginuser", password="ValidPass123!")
        
        # Login
        success, token = service.login(account="loginuser", password="ValidPass123!")
        assert success
        assert isinstance(token, str)
    
    def test_login_wrong_password(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        service.register(account="wrongpass", password="ValidPass123!")
        
        success, msg = service.login(account="wrongpass", password="WrongPass123!")
        assert not success
        assert "Invalid" in msg
    
    def test_get_user(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        success, user_id = service.register(
            account="getuser",
            password="ValidPass123!",
            nickname="Get User"
        )
        
        user = service.get_user(user_id)
        assert user is not None
        assert user.account == "getuser"
        assert user.nickname == "Get User"
    
    def test_update_user(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        success, user_id = service.register(
            account="updateuser",
            password="ValidPass123!"
        )
        
        success, msg = service.update_user(user_id, nickname="Updated Name")
        assert success
        
        user = service.get_user(user_id)
        assert user.nickname == "Updated Name"
    
    def test_delete_user(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        success, user_id = service.register(
            account="deleteuser",
            password="ValidPass123!"
        )
        
        success, msg = service.delete_user(user_id)
        assert success
        
        user = service.get_user(user_id)
        assert user.status == "deleted"
    
    def test_list_users(self):
        from acas_pro.services.user_service_v2 import UserService
        service = UserService()
        
        # Register multiple users
        for i in range(3):
            service.register(
                account=f"listuser{i}",
                password="ValidPass123!"
            )
        
        users = service.list_users(limit=10)
        assert len(users) >= 3
