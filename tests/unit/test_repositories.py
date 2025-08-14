"""
Unit tests for repository implementations.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.domain.models import Node, MindMapData, Position, UrgencyLevel
from src.infrastructure.repositories import (
    JsonMindMapRepository, InMemoryMindMapRepository, 
    RepositoryFactory, Result
)
from src.infrastructure.config import AppConfig


class TestResult:
    """Test cases for Result type."""
    
    def test_result_ok(self):
        """Test creating successful result."""
        result = Result.ok("test_data")
        assert result.is_ok()
        assert not result.is_error()
        assert result.data == "test_data"
        assert result.error is None
    
    def test_result_fail(self):
        """Test creating failed result."""
        result = Result.fail("test_error")
        assert not result.is_ok()
        assert result.is_error()
        assert result.data is None
        assert result.error == "test_error"


class TestInMemoryMindMapRepository:
    """Test cases for InMemoryMindMapRepository."""
    
    def test_save_and_load_empty(self):
        """Test saving and loading empty mind map."""
        repo = InMemoryMindMapRepository()
        mindmap = MindMapData()
        
        # Save
        result = repo.save(mindmap)
        assert result.is_ok()
        
        # Load
        result = repo.load()
        assert result.is_ok()
        assert len(result.data.nodes) == 0
    
    def test_save_and_load_with_nodes(self):
        """Test saving and loading mind map with nodes."""
        repo = InMemoryMindMapRepository()
        
        # Create test data
        node1 = Node(id=1, label="Node 1")
        node2 = Node(id=2, label="Node 2", parent_id=1)
        mindmap = MindMapData(nodes=[node1, node2], central_node_id=1)
        
        # Save
        result = repo.save(mindmap)
        assert result.is_ok()
        
        # Load
        result = repo.load()
        assert result.is_ok()
        loaded_mindmap = result.data
        
        assert len(loaded_mindmap.nodes) == 2
        assert loaded_mindmap.central_node_id == 1
        assert loaded_mindmap.find_node_by_id(1).label == "Node 1"
        assert loaded_mindmap.find_node_by_id(2).label == "Node 2"
    
    def test_load_without_save(self):
        """Test loading when no data has been saved."""
        repo = InMemoryMindMapRepository()
        result = repo.load()
        
        assert result.is_ok()
        assert len(result.data.nodes) == 0
    
    def test_backup_and_restore(self):
        """Test backup and restore functionality."""
        repo = InMemoryMindMapRepository()
        
        # Create and save initial data
        node = Node(id=1, label="Original")
        mindmap = MindMapData(nodes=[node])
        repo.save(mindmap)
        
        # Create backup
        backup_result = repo.backup()
        assert backup_result.is_ok()
        backup_id = backup_result.data
        
        # Modify data
        modified_node = Node(id=1, label="Modified")
        modified_mindmap = MindMapData(nodes=[modified_node])
        repo.save(modified_mindmap)
        
        # Verify modification
        result = repo.load()
        assert result.data.nodes[0].label == "Modified"
        
        # Restore from backup
        restore_result = repo.restore(backup_id)
        assert restore_result.is_ok()
        
        # Verify restoration
        result = repo.load()
        assert result.data.nodes[0].label == "Original"
    
    def test_backup_without_data(self):
        """Test backup when no data exists."""
        repo = InMemoryMindMapRepository()
        result = repo.backup()
        
        assert not result.is_ok()
        assert "No data to backup" in result.error
    
    def test_restore_invalid_backup(self):
        """Test restore with invalid backup ID."""
        repo = InMemoryMindMapRepository()
        result = repo.restore("invalid_backup")
        
        assert not result.is_ok()
        assert "Invalid backup path" in result.error
    
    def test_list_backups(self):
        """Test listing backups."""
        repo = InMemoryMindMapRepository()
        
        # Initially no backups
        result = repo.list_backups()
        assert result.is_ok()
        assert len(result.data) == 0
        
        # Create some backups
        node = Node(id=1, label="Test")
        mindmap = MindMapData(nodes=[node])
        repo.save(mindmap)
        
        repo.backup()
        repo.backup()
        
        # List backups
        result = repo.list_backups()
        assert result.is_ok()
        assert len(result.data) == 2
    
    def test_exists(self):
        """Test exists functionality."""
        repo = InMemoryMindMapRepository()
        
        # Initially no data
        assert not repo.exists()
        
        # After saving data
        mindmap = MindMapData()
        repo.save(mindmap)
        assert repo.exists()


class TestJsonMindMapRepository:
    """Test cases for JsonMindMapRepository."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a mock config
            config = Mock(spec=AppConfig)
            config.get_data_file_path.return_value = temp_path / "test_data.json"
            config.get_backup_dir_path.return_value = temp_path / "backups"
            
            yield config
    
    def test_save_and_load_empty(self, temp_config):
        """Test saving and loading empty mind map."""
        repo = JsonMindMapRepository(temp_config)
        mindmap = MindMapData()
        
        # Save
        result = repo.save(mindmap)
        assert result.is_ok()
        
        # Verify file exists
        assert temp_config.get_data_file_path().exists()
        
        # Load
        result = repo.load()
        assert result.is_ok()
        assert len(result.data.nodes) == 0
    
    def test_save_and_load_with_nodes(self, temp_config):
        """Test saving and loading mind map with nodes."""
        repo = JsonMindMapRepository(temp_config)
        
        # Create test data
        node1 = Node(id=1, label="Node 1", position=Position(10, 20))
        node2 = Node(id=2, label="Node 2", parent_id=1, urgency=UrgencyLevel.HIGH)
        mindmap = MindMapData(nodes=[node1, node2], central_node_id=1)
        
        # Save
        result = repo.save(mindmap)
        assert result.is_ok()
        
        # Load
        result = repo.load()
        assert result.is_ok()
        loaded_mindmap = result.data
        
        assert len(loaded_mindmap.nodes) == 2
        assert loaded_mindmap.central_node_id == 1
        
        loaded_node1 = loaded_mindmap.find_node_by_id(1)
        assert loaded_node1.label == "Node 1"
        assert loaded_node1.position.x == 10
        assert loaded_node1.position.y == 20
        
        loaded_node2 = loaded_mindmap.find_node_by_id(2)
        assert loaded_node2.label == "Node 2"
        assert loaded_node2.parent_id == 1
        assert loaded_node2.urgency == UrgencyLevel.HIGH
    
    def test_load_nonexistent_file(self, temp_config):
        """Test loading when file doesn't exist."""
        repo = JsonMindMapRepository(temp_config)
        result = repo.load()
        
        assert result.is_ok()
        assert len(result.data.nodes) == 0
    
    def test_load_invalid_json(self, temp_config):
        """Test loading invalid JSON file."""
        repo = JsonMindMapRepository(temp_config)
        
        # Create invalid JSON file
        data_file = temp_config.get_data_file_path()
        data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(data_file, 'w') as f:
            f.write("invalid json content")
        
        result = repo.load()
        assert not result.is_ok()
        assert "Invalid JSON" in result.error
    
    def test_save_validation_error(self, temp_config):
        """Test saving mind map with validation errors."""
        repo = JsonMindMapRepository(temp_config)
        
        # Create mind map with validation error (non-existent parent)
        node = Node(id=1, label="Test", parent_id=999)
        mindmap = MindMapData(nodes=[node])
        
        result = repo.save(mindmap)
        assert not result.is_ok()
        assert "Validation errors" in result.error
    
    def test_backup_and_restore(self, temp_config):
        """Test backup and restore functionality."""
        repo = JsonMindMapRepository(temp_config)
        
        # Create and save initial data
        node = Node(id=1, label="Original")
        mindmap = MindMapData(nodes=[node])
        repo.save(mindmap)
        
        # Create backup
        backup_result = repo.backup()
        assert backup_result.is_ok()
        backup_path = backup_result.data
        assert Path(backup_path).exists()
        
        # Modify data
        modified_node = Node(id=1, label="Modified")
        modified_mindmap = MindMapData(nodes=[modified_node])
        repo.save(modified_mindmap)
        
        # Verify modification
        result = repo.load()
        assert result.data.nodes[0].label == "Modified"
        
        # Restore from backup
        restore_result = repo.restore(backup_path)
        assert restore_result.is_ok()
        
        # Verify restoration
        result = repo.load()
        assert result.data.nodes[0].label == "Original"
    
    def test_backup_nonexistent_file(self, temp_config):
        """Test backup when data file doesn't exist."""
        repo = JsonMindMapRepository(temp_config)
        result = repo.backup()
        
        assert not result.is_ok()
        assert "No data file exists to backup" in result.error
    
    def test_restore_nonexistent_backup(self, temp_config):
        """Test restore with non-existent backup file."""
        repo = JsonMindMapRepository(temp_config)
        result = repo.restore("/nonexistent/backup.json")
        
        assert not result.is_ok()
        assert "Backup file does not exist" in result.error
    
    def test_restore_invalid_backup_json(self, temp_config):
        """Test restore with invalid backup JSON."""
        repo = JsonMindMapRepository(temp_config)
        
        # Create invalid backup file
        backup_dir = temp_config.get_backup_dir_path()
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / "invalid_backup.json"
        with open(backup_file, 'w') as f:
            f.write("invalid json")
        
        result = repo.restore(str(backup_file))
        assert not result.is_ok()
        assert "Invalid JSON in backup file" in result.error
    
    def test_list_backups(self, temp_config):
        """Test listing backups."""
        repo = JsonMindMapRepository(temp_config)
        
        # Initially no backups
        result = repo.list_backups()
        assert result.is_ok()
        assert len(result.data) == 0
        
        # Create some backups
        node = Node(id=1, label="Test")
        mindmap = MindMapData(nodes=[node])
        repo.save(mindmap)
        
        repo.backup()
        repo.backup()
        
        # List backups
        result = repo.list_backups()
        assert result.is_ok()
        assert len(result.data) == 2
        
        # Check backup info structure
        backup_info = result.data[0]
        assert "path" in backup_info
        assert "filename" in backup_info
        assert "created_at" in backup_info
        assert "size" in backup_info
    
    def test_exists(self, temp_config):
        """Test exists functionality."""
        repo = JsonMindMapRepository(temp_config)
        
        # Initially file doesn't exist
        assert not repo.exists()
        
        # After saving data
        mindmap = MindMapData()
        repo.save(mindmap)
        assert repo.exists()
    
    def test_get_file_info(self, temp_config):
        """Test getting file information."""
        repo = JsonMindMapRepository(temp_config)
        
        # File doesn't exist
        info = repo.get_file_info()
        assert not info["exists"]
        
        # After saving data
        mindmap = MindMapData()
        repo.save(mindmap)
        
        info = repo.get_file_info()
        assert info["exists"]
        assert "path" in info
        assert "size" in info
        assert "modified_at" in info
        assert "created_at" in info
    
    def test_cleanup_old_backups(self, temp_config):
        """Test cleaning up old backups."""
        repo = JsonMindMapRepository(temp_config)
        
        # Create test data and multiple backups
        node = Node(id=1, label="Test")
        mindmap = MindMapData(nodes=[node])
        repo.save(mindmap)
        
        # Create 5 backups
        import time
        for i in range(5):
            result = repo.backup()
            assert result.is_ok(), f"Backup {i+1} failed: {result.error}"
            time.sleep(0.001)  # Small delay to ensure unique timestamps
        
        # Verify 5 backups exist
        result = repo.list_backups()
        assert len(result.data) == 5
        
        # Cleanup, keeping only 3
        cleanup_result = repo.cleanup_old_backups(keep_count=3)
        assert cleanup_result.is_ok()
        
        # Verify only 3 backups remain
        result = repo.list_backups()
        assert len(result.data) == 3
    
    def test_atomic_write(self, temp_config):
        """Test atomic write functionality."""
        repo = JsonMindMapRepository(temp_config)
        
        # Create initial data
        node = Node(id=1, label="Test")
        mindmap = MindMapData(nodes=[node])
        
        # Mock file operations to simulate failure during write
        with patch('shutil.move', side_effect=Exception("Simulated failure")):
            result = repo.save(mindmap)
            assert not result.is_ok()
            
            # Original file should not exist (atomic write failed)
            assert not temp_config.get_data_file_path().exists()
            
            # Temporary file should be cleaned up
            temp_file = temp_config.get_data_file_path().with_suffix('.tmp')
            assert not temp_file.exists()


class TestRepositoryFactory:
    """Test cases for RepositoryFactory."""
    
    def test_create_json_repository(self):
        """Test creating JSON repository."""
        config = Mock(spec=AppConfig)
        repo = RepositoryFactory.create_repository(config, "json")
        
        assert isinstance(repo, JsonMindMapRepository)
    
    def test_create_unknown_repository(self):
        """Test creating unknown repository type."""
        config = Mock(spec=AppConfig)
        
        with pytest.raises(ValueError, match="Unknown repository type"):
            RepositoryFactory.create_repository(config, "unknown")