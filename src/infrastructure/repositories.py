"""
Repository implementations for the Enhanced Mind Map application.

This module provides the repository pattern implementation for data persistence,
including abstract interfaces and concrete implementations.
"""

import json
import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import logging

from src.domain.models import MindMapData, ValidationError
from src.infrastructure.config import AppConfig


class RepositoryError(Exception):
    """Base exception for repository operations."""
    
    def __init__(self, message: str, operation: str, original_error: Optional[Exception] = None):
        self.message = message
        self.operation = operation
        self.original_error = original_error
        super().__init__(message)


class Result:
    """Result type for repository operations."""
    
    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error
    
    @classmethod
    def ok(cls, data: Any = None) -> 'Result':
        """Create a successful result."""
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: str) -> 'Result':
        """Create a failed result."""
        return cls(success=False, error=error)
    
    def is_ok(self) -> bool:
        """Check if the result is successful."""
        return self.success
    
    def is_error(self) -> bool:
        """Check if the result is an error."""
        return not self.success


class MindMapRepository(ABC):
    """Abstract base class for mind map data repositories."""
    
    @abstractmethod
    def save(self, mindmap: MindMapData) -> Result:
        """
        Save mind map data.
        
        Args:
            mindmap: The MindMapData to save
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    def load(self) -> Result:
        """
        Load mind map data.
        
        Returns:
            Result containing MindMapData or error
        """
        pass
    
    @abstractmethod
    def backup(self) -> Result:
        """
        Create a backup of the current data.
        
        Returns:
            Result containing backup file path or error
        """
        pass
    
    @abstractmethod
    def restore(self, backup_path: str) -> Result:
        """
        Restore data from a backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    def list_backups(self) -> Result:
        """
        List available backups.
        
        Returns:
            Result containing list of backup file paths
        """
        pass
    
    @abstractmethod
    def exists(self) -> bool:
        """
        Check if the data source exists.
        
        Returns:
            True if data source exists, False otherwise
        """
        pass


class JsonMindMapRepository(MindMapRepository):
    """JSON file-based implementation of MindMapRepository."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.data_file = config.get_data_file_path()
        self.backup_dir = config.get_backup_dir_path()
        
        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, mindmap: MindMapData) -> Result:
        """Save mind map data to JSON file with atomic write."""
        try:
            # Validate the mind map data
            validation_errors = mindmap.validate_relationships()
            if validation_errors:
                error_messages = [error.message for error in validation_errors]
                return Result.fail(f"Validation errors: {'; '.join(error_messages)}")
            
            # Convert to dictionary
            data_dict = mindmap.to_dict()
            
            # Create temporary file for atomic write
            temp_file = self.data_file.with_suffix('.tmp')
            
            # Write to temporary file
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)
            
            # Atomic move to final location
            shutil.move(str(temp_file), str(self.data_file))
            
            self.logger.info(f"Successfully saved mind map data to {self.data_file}")
            return Result.ok()
            
        except Exception as e:
            self.logger.error(f"Error saving mind map data: {str(e)}")
            # Clean up temporary file if it exists
            temp_file = self.data_file.with_suffix('.tmp')
            if temp_file.exists():
                temp_file.unlink()
            return Result.fail(f"Failed to save data: {str(e)}")
    
    def load(self) -> Result:
        """Load mind map data from JSON file."""
        try:
            if not self.data_file.exists():
                self.logger.info("Data file does not exist, returning empty mind map")
                return Result.ok(MindMapData())
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data_dict = json.load(f)
            
            # Convert from dictionary to domain model
            mindmap = MindMapData.from_dict(data_dict)
            
            # Validate the loaded data
            validation_errors = mindmap.validate_relationships()
            if validation_errors:
                self.logger.warning(f"Loaded data has validation errors: {validation_errors}")
                # Still return the data but log the issues
            
            self.logger.info(f"Successfully loaded mind map data from {self.data_file}")
            return Result.ok(mindmap)
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in data file: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
        
        except Exception as e:
            error_msg = f"Error loading mind map data: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    def backup(self) -> Result:
        """Create a backup of the current data file."""
        try:
            if not self.data_file.exists():
                return Result.fail("No data file exists to backup")
            
            # Generate backup filename with timestamp including microseconds
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_filename = f"mindmap_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            # Copy the data file to backup location
            shutil.copy2(str(self.data_file), str(backup_path))
            
            self.logger.info(f"Created backup at {backup_path}")
            return Result.ok(str(backup_path))
            
        except Exception as e:
            error_msg = f"Error creating backup: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    def restore(self, backup_path: str) -> Result:
        """Restore data from a backup file."""
        try:
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                return Result.fail(f"Backup file does not exist: {backup_path}")
            
            # Validate the backup file by trying to load it
            with open(backup_file, 'r', encoding='utf-8') as f:
                data_dict = json.load(f)
            
            # Try to create MindMapData to validate structure
            mindmap = MindMapData.from_dict(data_dict)
            
            # Create a backup of current data before restoring
            current_backup_result = self.backup()
            if not current_backup_result.is_ok():
                self.logger.warning(f"Could not backup current data: {current_backup_result.error}")
            
            # Copy backup file to data file location
            shutil.copy2(str(backup_file), str(self.data_file))
            
            self.logger.info(f"Successfully restored data from {backup_path}")
            return Result.ok()
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in backup file: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
        
        except Exception as e:
            error_msg = f"Error restoring from backup: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    def list_backups(self) -> Result:
        """List all available backup files."""
        try:
            if not self.backup_dir.exists():
                return Result.ok([])
            
            # Find all JSON files in backup directory
            backup_files = []
            for file_path in self.backup_dir.glob("mindmap_backup_*.json"):
                backup_info = {
                    "path": str(file_path),
                    "filename": file_path.name,
                    "created_at": datetime.fromtimestamp(file_path.stat().st_mtime),
                    "size": file_path.stat().st_size,
                }
                backup_files.append(backup_info)
            
            # Sort by creation time (newest first)
            backup_files.sort(key=lambda x: x["created_at"], reverse=True)
            
            self.logger.debug(f"Found {len(backup_files)} backup files")
            return Result.ok(backup_files)
            
        except Exception as e:
            error_msg = f"Error listing backups: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    def exists(self) -> bool:
        """Check if the data file exists."""
        return self.data_file.exists()
    
    def get_file_info(self) -> Dict[str, Any]:
        """Get information about the data file."""
        if not self.data_file.exists():
            return {"exists": False}
        
        stat = self.data_file.stat()
        return {
            "exists": True,
            "path": str(self.data_file),
            "size": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "created_at": datetime.fromtimestamp(stat.st_ctime),
        }
    
    def cleanup_old_backups(self, keep_count: int = 10) -> Result:
        """Clean up old backup files, keeping only the most recent ones."""
        try:
            backups_result = self.list_backups()
            if not backups_result.is_ok():
                return backups_result
            
            backups = backups_result.data
            if len(backups) <= keep_count:
                return Result.ok(f"No cleanup needed, {len(backups)} backups exist")
            
            # Remove oldest backups
            backups_to_remove = backups[keep_count:]
            removed_count = 0
            
            for backup in backups_to_remove:
                try:
                    Path(backup["path"]).unlink()
                    removed_count += 1
                except Exception as e:
                    self.logger.warning(f"Could not remove backup {backup['path']}: {str(e)}")
            
            message = f"Cleaned up {removed_count} old backup files"
            self.logger.info(message)
            return Result.ok(message)
            
        except Exception as e:
            error_msg = f"Error cleaning up backups: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)


class RepositoryFactory:
    """Factory for creating repository instances."""
    
    @staticmethod
    def create_repository(config: AppConfig, repository_type: str = "json") -> MindMapRepository:
        """
        Create a repository instance.
        
        Args:
            config: Application configuration
            repository_type: Type of repository to create ("json", "memory", etc.)
            
        Returns:
            MindMapRepository instance
        """
        if repository_type.lower() == "json":
            return JsonMindMapRepository(config)
        else:
            raise ValueError(f"Unknown repository type: {repository_type}")


class InMemoryMindMapRepository(MindMapRepository):
    """In-memory implementation for testing purposes."""
    
    def __init__(self):
        self.data: Optional[MindMapData] = None
        self.backups: List[MindMapData] = []
        self.logger = logging.getLogger(__name__)
    
    def save(self, mindmap: MindMapData) -> Result:
        """Save mind map data in memory."""
        try:
            # Validate the mind map data
            validation_errors = mindmap.validate_relationships()
            if validation_errors:
                error_messages = [error.message for error in validation_errors]
                return Result.fail(f"Validation errors: {'; '.join(error_messages)}")
            
            self.data = mindmap
            return Result.ok()
            
        except Exception as e:
            return Result.fail(f"Failed to save data: {str(e)}")
    
    def load(self) -> Result:
        """Load mind map data from memory."""
        if self.data is None:
            return Result.ok(MindMapData())
        return Result.ok(self.data)
    
    def backup(self) -> Result:
        """Create a backup in memory."""
        if self.data is None:
            return Result.fail("No data to backup")
        
        # Create a deep copy for backup
        import copy
        backup_data = copy.deepcopy(self.data)
        self.backups.append(backup_data)
        
        backup_id = f"backup_{len(self.backups)}"
        return Result.ok(backup_id)
    
    def restore(self, backup_path: str) -> Result:
        """Restore data from memory backup."""
        try:
            backup_index = int(backup_path.split("_")[1]) - 1
            if 0 <= backup_index < len(self.backups):
                import copy
                self.data = copy.deepcopy(self.backups[backup_index])
                return Result.ok()
            else:
                return Result.fail(f"Invalid backup index: {backup_index}")
        except (ValueError, IndexError):
            return Result.fail(f"Invalid backup path: {backup_path}")
    
    def list_backups(self) -> Result:
        """List available backups in memory."""
        backup_list = []
        for i, backup in enumerate(self.backups):
            backup_info = {
                "path": f"backup_{i + 1}",
                "filename": f"backup_{i + 1}",
                "created_at": datetime.now(),  # Simplified for testing
                "size": len(str(backup.to_dict())),
            }
            backup_list.append(backup_info)
        
        return Result.ok(backup_list)
    
    def exists(self) -> bool:
        """Check if data exists in memory."""
        return self.data is not None