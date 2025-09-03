# Obsolete Files List - Not Relevant for New Architecture

## 🗑️ **Files Safe to Remove**

### **Legacy Main Application**
- `main.py` - Old main application file (replaced by `main_new.py`)

### **Legacy Core Modules (No longer used by new architecture)**
- `src/handlers.py` - Old message handlers (replaced by event system)
- `src/message_queue.py` - Old message queue system (replaced by event system)
- `src/canvas_utils.py` - Old canvas utilities (functionality moved to service layer)
- `src/node_utils.py` - Old node utilities (replaced by domain models and services)
- `src/position_utils.py` - Old position utilities (replaced by domain models)

### **Legacy State Management (Partially obsolete)**
- `src/state.py` - Old state management (mostly replaced by service adapter, but still used by some UI components)
- `src/history.py` - Old undo/redo system (needs integration with new architecture)

### **Legacy JavaScript Files**
- `src/message_utils.js` - Old JavaScript message utilities
- `src/network_handlers.js` - Old network event handlers
- `src/utils.js` - Old JavaScript utilities

### **Test Files for Legacy Systems**
- `tests/check_position_export.py` - Tests old position export
- `tests/debug_position_flow.py` - Debug old message flow
- `tests/node_lifecycle_test.py` - Tests old node lifecycle
- `tests/simple_position_test.py` - Tests old position system
- `tests/test_dragend_integration.py` - Tests old drag system
- `tests/test_node_position.py` - Tests old position system
- `tests/verify_position_fix.py` - Verifies old position fixes
- `tests/integration/test_basic_operations.py` - Tests old message queue
- `tests/integration/test_canvas_events.py` - Tests old canvas events
- `tests/integration/test_core_functionality.py` - Tests old core functionality
- `tests/integration/test_dragend_integration.py` - Tests old drag system
- `tests/integration/test_message_flow.py` - Tests old message flow
- `tests/e2e/test_error_handling.py` - Tests old error handling
- `tests/e2e/verify_position_fix.py` - Verifies old position fixes
- `tests/utils/debug_position_flow.py` - Debug utilities for old system

### **Development/Debug Files**
- `simple_test.py` - Simple test file
- `test_direct_import.py` - Direct import test
- `test_enum.py` - Enum test
- `test_import.py` - Import test
- `test_minimal.py` - Minimal test
- `test_node_creation.py` - Node creation test
- `test_ui_comm.py` - UI communication test
- `fix_unicode.py` - Unicode fix utility

### **Documentation Files (Migration-related)**
- `canvas_refactoring.md` - Old refactoring documentation
- `network_visualization_refactoring.md` - Old refactoring documentation
- `refactoring_summary.md` - Old refactoring summary
- `deprecated_modules.txt` - List of deprecated modules
- `COMPONENTS_MIGRATION_PLAN.md` - Migration planning document
- `COMPONENTS_MIGRATION_STATUS.md` - Migration status document
- `DELETE_CENTER_NODE_FIX.md` - Specific fix documentation
- `CURRENT_APP_STATUS.md` - Old app status
- `APP_FUNCTIONALITY_FIXES.md` - Old functionality fixes
- `IMPLEMENTATION_PROGRESS.md` - Implementation progress tracking
- `PHASE_4_COMPLETION_SUMMARY.md` - Phase completion summary
- `TASK_8_1_COMPLETION_SUMMARY.md` - Task completion summary
- `TASK_8_2_COMPLETION_SUMMARY.md` - Task completion summary
- `TASK_8_3_COMPLETION_SUMMARY.md` - Task completion summary
- `TASK_8_4_COMPLETION_SUMMARY.md` - Task completion summary
- `TEST_FIXES_SUMMARY.md` - Test fixes summary
- `FINAL_MIGRATION_COMPLETION.md` - Final migration summary

### **Test Scripts and Utilities**
- `tests/run_position_tests.py` - Run old position tests
- `tests/run_tests.py` - Run old test suite
- `tests/reorganize_tests.py` - Test reorganization script
- `tests/scripts/` - Directory with old test scripts

### **JavaScript Test Files**
- `tests/position_format_test.js` - JavaScript position tests
- `tests/simple_dragend_test.js` - JavaScript drag tests
- `tests/test_dragend_event.js` - JavaScript drag event tests

### **Log Files (Can be cleaned up)**
- `debug_test_run.log` - Debug log file
- `events.jsonl` - Events log file
- All files in `logs/` directory (old session logs)
- All files in `test_logs/` directory (old test logs)

## ⚠️ **Files to Keep (Still Used by New Architecture)**

### **Core New Architecture Files**
- `main_new.py` - New main application
- `src/integration/service_adapter.py` - Service adapter
- `src/domain/models.py` - Domain models
- `src/application/services.py` - Application services
- `src/infrastructure/` - All infrastructure files
- All files in `tests/unit/` and `tests/integration/` for new architecture

### **UI Components (Migrated)**
- All files in `src/ui/` - UI components (migrated to use service adapter)

### **Configuration and Utilities**
- `src/config.py` - Configuration (still used)
- `src/themes.py` - Themes (still used)
- `src/utils.py` - Utilities (partially migrated, still used)
- `src/logging_setup.py` - Logging setup (still used)

### **Legacy Files Still in Use (Need Further Migration)**
- `src/events.py` - Event handlers (migrated but still used)
- `src/message_handler.py` - Message handler (migrated but still used)

## 📊 **Summary**

### **Safe to Remove:**
- **1 main file** (main.py)
- **5 core legacy modules** (handlers.py, message_queue.py, canvas_utils.py, node_utils.py, position_utils.py)
- **3 JavaScript files** (message_utils.js, network_handlers.js, utils.js)
- **15+ test files** for legacy systems
- **15+ documentation files** from migration process
- **3 JavaScript test files**
- **Multiple log files** and debug files

### **Total Files to Remove: ~50+ files**

### **Benefits of Cleanup:**
- ✅ Cleaner codebase
- ✅ Reduced confusion about which files to use
- ✅ Smaller repository size
- ✅ Easier maintenance
- ✅ Clear separation between old and new architecture

### **Recommended Action:**
1. **Create a backup** of the current state
2. **Remove obsolete files** in batches
3. **Test application** after each batch removal
4. **Update any remaining imports** that might reference removed files