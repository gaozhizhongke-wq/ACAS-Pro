"""
ACAS Pro - Dependency Injection Container
Production-grade DI framework for testable architecture
"""

from typing import Dict, Type, TypeVar, Callable, Any, Optional
from functools import wraps
import threading

T = TypeVar("T")


class DIContainer:
    """
    Dependency Injection Container

    Usage:
        container = DIContainer()

        # Register singleton
        container.register_singleton(Config, lambda: Config.load())

        # Register factory
        container.register_factory(DatabaseManager, lambda c: DatabaseManager(c.resolve(Config)))

        # Resolve dependency
        db = container.resolve(DatabaseManager)
    """

    def __init__(self):
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[["DIContainer"], Any]] = {}
        self._lock = threading.RLock()
        self._resolving: set = set()

    def register_singleton(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a singleton service"""
        self._factories[interface] = lambda c: factory()

    def register_factory(
        self, interface: Type[T], factory: Callable[["DIContainer"], T]
    ) -> None:
        """Register a factory service (new instance each time)"""
        self._factories[interface] = factory

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register an existing instance"""
        self._singletons[interface] = instance

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency"""
        with self._lock:
            if interface in self._resolving:
                raise RuntimeError(f"Circular dependency detected for {interface}")
            self._resolving.add(interface)
            try:
                # Return existing singleton
                if interface in self._singletons:
                    return self._singletons[interface]

                # Create from factory
                if interface in self._factories:
                    instance = self._factories[interface](self)
                    # Cache singletons
                    self._singletons[interface] = instance
                    return instance

                raise KeyError(f"No registration for {interface}")
            finally:
                self._resolving.discard(interface)

    def clear(self) -> None:
        """Clear all registrations (for testing)"""
        with self._lock:
            self._singletons.clear()
            self._factories.clear()

    def is_registered(self, interface: Type) -> bool:
        """Check if interface is registered"""
        return interface in self._singletons or interface in self._factories


# Global container (lazy-loaded)
_container: Optional[DIContainer] = None
_container_lock = threading.Lock()


def get_container() -> DIContainer:
    """Get global DI container (lazy-loaded)"""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = DIContainer()
    return _container


def reset_container() -> None:
    """Reset container (for testing)"""
    global _container
    with _container_lock:
        _container = None


def inject(interface: Type[T]) -> Callable:
    """Decorator for dependency injection

    Usage:
        @inject(Config)
        def my_function(config: Config):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> None:
            container = get_container()
            if interface not in kwargs:
                kwargs[interface.__name__.lower()] = container.resolve(interface)
            return func(*args, **kwargs)

        return wrapper

    return decorator
