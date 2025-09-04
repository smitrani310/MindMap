#!/usr/bin/env python3
"""
Test Sync Fix

This script tests if the synchronization issue has been fixed.
"""

import streamlit as st
import logging

# Configure logging to see debug messages
logging.basicConfig(level=logging.DEBUG)

st.set_page_config(page_title="Test Sync Fix", layout="wide")

st.title("🔧 Test Sync Fix")

st.markdown("""
This test verifies that the synchronization issue between canvas interactions 
and node data availability has been fixed.
""")

# Test 1: Service Adapter Initialization
st.subheader("Test 1: Service Adapter Initialization")

try:
    from src.integration.service_adapter import get_service_adapter
    adapter = get_service_adapter()
    
    st.success("✅ Service adapter created successfully")
    st.write(f"**Adapter Type:** {type(adapter)}")
    st.write(f"**Initialized:** {getattr(adapter, '_initialized', 'Unknown')}")
    
except Exception as e:
    st.error(f"❌ Service adapter failed: {e}")

# Test 2: Get Ideas
st.subheader("Test 2: Get Ideas")

try:
    ideas = adapter.get_ideas()
    st.success(f"✅ Got {len(ideas)} ideas from adapter")
    
    if ideas:
        st.write("**Sample Ideas:**")
        for i, idea in enumerate(ideas[:3]):
            st.write(f"- **{idea.get('label', 'Untitled')}** (ID: {idea.get('id')}) at ({idea.get('x', 0)}, {idea.get('y', 0)})")
    else:
        st.warning("⚠️ No ideas found - this might indicate the sync issue")
        
except Exception as e:
    st.error(f"❌ Get ideas failed: {e}")
    import traceback
    st.code(traceback.format_exc())

# Test 3: Service Layer Direct Access
st.subheader("Test 3: Service Layer Direct Access")

try:
    service = adapter.service
    nodes = service.get_all_nodes()
    
    st.success(f"✅ Got {len(nodes)} nodes from service")
    
    if nodes:
        st.write("**Sample Nodes:**")
        for i, node in enumerate(nodes[:3]):
            st.write(f"- **{node.label}** (ID: {node.id}) at ({node.position.x if node.position else 0}, {node.position.y if node.position else 0})")
    else:
        st.warning("⚠️ No nodes found in service")
        
except Exception as e:
    st.error(f"❌ Service access failed: {e}")
    import traceback
    st.code(traceback.format_exc())

# Test 4: Simulate Canvas Click Processing
st.subheader("Test 4: Simulate Canvas Click Processing")

if st.button("🖱️ Simulate Canvas Click"):
    try:
        # Simulate the same process that happens during canvas clicks
        from src.events import handle_canvas_click
        
        payload = {
            'x': 100,
            'y': 100,
            'canvasWidth': 400,
            'canvasHeight': 300
        }
        
        st.info("Processing simulated canvas click...")
        
        # This should now work without the sync issue
        success = handle_canvas_click(payload, 'canvas_click')
        
        if success:
            st.success("✅ Canvas click processed successfully!")
        else:
            st.warning("⚠️ Canvas click processed but no node found (expected if click is not near a node)")
            
    except Exception as e:
        st.error(f"❌ Canvas click simulation failed: {e}")
        import traceback
        st.code(traceback.format_exc())

# Test 5: Check Repository Data
st.subheader("Test 5: Check Repository Data")

try:
    from src.infrastructure.repositories import get_repository
    repo = get_repository()
    result = repo.load()
    
    if result.is_ok():
        data = result.data
        st.success(f"✅ Repository loaded {len(data.nodes)} nodes")
        
        if data.nodes:
            st.write("**Repository Nodes:**")
            for node in data.nodes[:3]:
                st.write(f"- **{node.label}** (ID: {node.id})")
    else:
        st.error(f"❌ Repository load failed: {result.error}")
        
except Exception as e:
    st.error(f"❌ Repository check failed: {e}")

# Summary
st.subheader("📊 Test Summary")

st.markdown("""
**What to look for:**

✅ **All tests pass**: Sync issue is fixed  
⚠️ **Service adapter works but no ideas**: Data loading issue  
❌ **Service adapter fails**: Initialization problem  

**Expected behavior after fix:**
- Service adapter should initialize properly
- get_ideas() should return the available nodes
- Canvas click simulation should process without errors
- Repository should contain the mind map data
""")

st.info("👆 Run through these tests to verify the sync fix is working")