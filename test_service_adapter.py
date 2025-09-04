#!/usr/bin/env python3
"""
Service Adapter Test

Test the service adapter initialization in isolation.
"""

import streamlit as st
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# st.set_page_config(page_title="Service Adapter Test", layout="wide")  # Skip to avoid conflicts

st.title("🔧 Service Adapter Test")

st.markdown("""
This test checks if the service adapter can be initialized.
""")

# Test 1: Basic imports
st.subheader("1. Testing Imports")
try:
    from src.integration.service_adapter import ServiceAdapter, init_service_adapter
    st.success("✅ Service adapter imports successful")
except Exception as e:
    st.error(f"❌ Import error: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

# Test 2: Configuration
st.subheader("2. Testing Configuration")
try:
    from src.infrastructure.config import ConfigFactory
    config = ConfigFactory.create_config()
    st.success(f"✅ Configuration created: {type(config)}")
    st.write(f"Data file: {config.data_file}")
    st.write(f"Environment: {config.environment}")
except Exception as e:
    st.error(f"❌ Configuration error: {e}")
    import traceback
    st.code(traceback.format_exc())

# Test 3: Repository
st.subheader("3. Testing Repository")
try:
    from src.infrastructure.repositories import RepositoryFactory
    config = ConfigFactory.create_config()
    repository = RepositoryFactory.create_repository(config, "json")
    st.success(f"✅ Repository created: {type(repository)}")
except Exception as e:
    st.error(f"❌ Repository error: {e}")
    import traceback
    st.code(traceback.format_exc())

# Test 4: Service Adapter
st.subheader("4. Testing Service Adapter")
try:
    adapter = init_service_adapter()
    st.success(f"✅ Service adapter created: {type(adapter)}")
    
    # Test basic functionality
    ideas = adapter.get_ideas()
    st.write(f"Ideas loaded: {len(ideas)}")
    
    central = adapter.get_central()
    st.write(f"Central node: {central}")
    
except Exception as e:
    st.error(f"❌ Service adapter error: {e}")
    import traceback
    st.code(traceback.format_exc())

st.markdown("""
**Expected behavior:**
- ✅ All imports should succeed
- ✅ Configuration should be created
- ✅ Repository should be created
- ✅ Service adapter should initialize
- ✅ Ideas should be loaded from data file

**If any step fails:**
- Check the error details above
- Verify that all dependencies are installed
- Check if the data file exists
""")