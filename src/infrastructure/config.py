"""
Centralized configuration management for the Enhanced Mind Map application.

This module provides a Pydantic-based configuration system that supports:
- Environment variable overrides
- Multiple environment configurations
- Validation and type checking
- Default fallbacks
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

from pydantic import Field, validator
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="MINDMAP_ENV")
    debug: bool = Field(default=True, env="MINDMAP_DEBUG")
    
    # File paths
    data_file: str = Field(default="mindmap_data.json", env="MINDMAP_DATA_FILE")
    backup_dir: str = Field(default="backups", env="MINDMAP_BACKUP_DIR")
    log_dir: str = Field(default="logs", env="MINDMAP_LOG_DIR")
    
    # Application settings
    theme: str = Field(default="default", env="MINDMAP_THEME")
    canvas_width: int = Field(default=800, env="MINDMAP_CANVAS_WIDTH")
    canvas_height: int = Field(default=600, env="MINDMAP_CANVAS_HEIGHT")
    auto_save_interval: int = Field(default=30, env="MINDMAP_AUTO_SAVE_INTERVAL")  # seconds
    
    # Performance settings
    cache_size: int = Field(default=1000, env="MINDMAP_CACHE_SIZE")
    max_nodes: int = Field(default=10000, env="MINDMAP_MAX_NODES")
    render_batch_size: int = Field(default=100, env="MINDMAP_RENDER_BATCH_SIZE")
    
    # Logging configuration
    log_level: LogLevel = Field(default=LogLevel.INFO, env="MINDMAP_LOG_LEVEL")
    log_rotation_size: str = Field(default="10MB", env="MINDMAP_LOG_ROTATION_SIZE")
    log_retention_days: int = Field(default=30, env="MINDMAP_LOG_RETENTION_DAYS")
    
    # Network and visualization settings
    network_physics_enabled: bool = Field(default=True, env="MINDMAP_PHYSICS_ENABLED")
    network_stabilization_iterations: int = Field(default=100, env="MINDMAP_STABILIZATION_ITERATIONS")
    
    # Security settings
    max_file_size_mb: int = Field(default=50, env="MINDMAP_MAX_FILE_SIZE_MB")
    allowed_file_extensions: List[str] = Field(
        default=[".json", ".txt", ".md"], 
        env="MINDMAP_ALLOWED_EXTENSIONS"
    )
    
    # Feature flags
    enable_real_time_sync: bool = Field(default=False, env="MINDMAP_REAL_TIME_SYNC")
    enable_collaboration: bool = Field(default=False, env="MINDMAP_COLLABORATION")
    enable_analytics: bool = Field(default=False, env="MINDMAP_ANALYTICS")
    
    class Config:
        env_file = ".env"
        env_prefix = "MINDMAP_"
        case_sensitive = False
        
    @validator("data_file")
    def validate_data_file(cls, v):
        """Ensure data file has proper extension."""
        if not v.endswith('.json'):
            raise ValueError("Data file must have .json extension")
        return v
    
    @validator("cache_size")
    def validate_cache_size(cls, v):
        """Ensure cache size is reasonable."""
        if v < 10 or v > 100000:
            raise ValueError("Cache size must be between 10 and 100000")
        return v
    
    @validator("max_nodes")
    def validate_max_nodes(cls, v):
        """Ensure max nodes is reasonable."""
        if v < 1 or v > 1000000:
            raise ValueError("Max nodes must be between 1 and 1000000")
        return v
    
    @validator("auto_save_interval")
    def validate_auto_save_interval(cls, v):
        """Ensure auto save interval is reasonable."""
        if v < 5 or v > 3600:  # 5 seconds to 1 hour
            raise ValueError("Auto save interval must be between 5 and 3600 seconds")
        return v
    
    def get_data_file_path(self) -> Path:
        """Get the full path to the data file."""
        return Path(self.data_file).resolve()
    
    def get_backup_dir_path(self) -> Path:
        """Get the full path to the backup directory."""
        return Path(self.backup_dir).resolve()
    
    def get_log_dir_path(self) -> Path:
        """Get the full path to the log directory."""
        return Path(self.log_dir).resolve()
    
    def ensure_directories_exist(self) -> None:
        """Create necessary directories if they don't exist."""
        self.get_backup_dir_path().mkdir(parents=True, exist_ok=True)
        self.get_log_dir_path().mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()


class DevelopmentConfig(AppConfig):
    """Development environment configuration."""
    debug: bool = True
    log_level: LogLevel = LogLevel.DEBUG
    cache_size: int = 100
    auto_save_interval: int = 10  # More frequent saves in development


class TestingConfig(AppConfig):
    """Testing environment configuration."""
    debug: bool = True
    log_level: LogLevel = LogLevel.WARNING
    data_file: str = "test_mindmap_data.json"
    backup_dir: str = "test_backups"
    log_dir: str = "test_logs"
    cache_size: int = 50
    auto_save_interval: int = 5
    max_nodes: int = 1000  # Smaller limits for testing


class ProductionConfig(AppConfig):
    """Production environment configuration."""
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    cache_size: int = 5000
    auto_save_interval: int = 60  # Less frequent saves in production
    log_retention_days: int = 90  # Keep logs longer in production


class ConfigFactory:
    """Factory for creating configuration instances."""
    
    @staticmethod
    def create_config(env: Optional[str] = None) -> AppConfig:
        """
        Create configuration instance based on environment.
        
        Args:
            env: Environment name. If None, uses MINDMAP_ENV environment variable
                 or defaults to 'development'.
        
        Returns:
            AppConfig instance for the specified environment.
        """
        if env is None:
            env = os.getenv("MINDMAP_ENV", Environment.DEVELOPMENT.value)
        
        env = env.lower()
        
        if env == Environment.PRODUCTION.value:
            return ProductionConfig()
        elif env == Environment.TESTING.value:
            return TestingConfig()
        else:
            return DevelopmentConfig()
    
    @staticmethod
    def create_from_file(config_file: str) -> AppConfig:
        """
        Create configuration from a specific file.
        
        Args:
            config_file: Path to the configuration file.
        
        Returns:
            AppConfig instance loaded from the file.
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        # Create a temporary config to load from the specific file
        class FileConfig(AppConfig):
            class Config:
                env_file = config_file
        
        return FileConfig()


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get the global configuration instance.
    
    Returns:
        The global AppConfig instance.
    """
    global _config
    if _config is None:
        _config = ConfigFactory.create_config()
        _config.ensure_directories_exist()
    return _config


def set_config(config: AppConfig) -> None:
    """
    Set the global configuration instance.
    
    Args:
        config: The AppConfig instance to set as global.
    """
    global _config
    _config = config
    _config.ensure_directories_exist()


def reload_config() -> AppConfig:
    """
    Reload the global configuration from environment.
    
    Returns:
        The reloaded AppConfig instance.
    """
    global _config
    _config = None
    return get_config()