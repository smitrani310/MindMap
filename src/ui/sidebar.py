"""Sidebar component for the Enhanced Mind Map application."""

import streamlit as st
import colorsys
from typing import Dict, Any, List

from src.state import get_store, get_current_theme, set_current_theme, save_data
from src.themes import THEMES, TAGS
from src.config import DEFAULT_SETTINGS

def render_sidebar():
    """
    Render the sidebar with theme selection and other settings.
    """
    with st.sidebar.expander("Settings", expanded=False):
        selected_theme = st.selectbox(
            "Select Theme",
            options=list(THEMES.keys()),
            index=list(THEMES.keys()).index(get_current_theme())
        )
        
        # Update theme if changed
        if selected_theme != get_current_theme():
            set_current_theme(selected_theme)
            save_data(get_store())
            st.rerun()
        
        # Get settings with defaults
        settings = get_store().get('settings', {})
        default_edge_length = settings.get('edge_length', DEFAULT_SETTINGS['edge_length'])
        default_spring_strength = settings.get('spring_strength', DEFAULT_SETTINGS['spring_strength'])
        default_size_multiplier = settings.get('size_multiplier', DEFAULT_SETTINGS['size_multiplier'])
        
        # Add connection length slider
        edge_length = st.slider(
            "Connection Length", 
            min_value=50, 
            max_value=300, 
            value=default_edge_length,
            step=10,
            help="Adjust the length of connections between nodes"
        )
        
        # Add spring strength slider
        spring_strength = st.slider(
            "Connection Strength",
            min_value=0.1,
            max_value=1.0,
            value=default_spring_strength,
            step=0.1,
            help="Adjust how strongly connected nodes pull together (higher = tighter grouping)"
        )
        
        # Add size multiplier for urgency differences
        size_multiplier = st.slider(
            "Urgency Size Impact",
            min_value=1.0,
            max_value=3.0,
            value=default_size_multiplier,
            step=0.2,
            help="Enhance the size difference between urgency levels (higher = more pronounced difference)"
        )
        
        # Get custom colors or use defaults
        custom_colors = settings.get('custom_colors', DEFAULT_SETTINGS['custom_colors'])
        
        # Custom Tags Management
        st.markdown("### Tag Management")
        
        # Get existing custom tags
        custom_tags = settings.get('custom_tags', [])
        
        # Input for adding new custom tags
        new_tag_col1, new_tag_col2 = st.columns([3, 1])
        new_tag = new_tag_col1.text_input("New Custom Tag", key="new_custom_tag")
        
        add_tag_clicked = new_tag_col2.button("Add Tag")
        if add_tag_clicked and new_tag and new_tag not in custom_tags and new_tag not in TAGS:
            # Generate a color for the new tag
            hash_value = sum(ord(c) for c in new_tag)
            hue = hash_value % 360
            
            # Convert HSL to hex for the color picker
            h, s, l = hue/360.0, 0.7, 0.6  # convert to 0-1 range
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            hex_color = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
            
            # Add the tag to custom tags list
            custom_tags.append(new_tag)
            
            # Add the tag color to custom colors
            if 'tags' not in custom_colors:
                custom_colors['tags'] = {}
            custom_colors['tags'][new_tag] = hex_color
            
            # Save changes
            settings['custom_tags'] = custom_tags
            settings['custom_colors'] = custom_colors
            get_store()['settings'] = settings
            
            save_data(get_store())
            st.rerun()
            
        # Display custom tags for removal and color editing
        if custom_tags:
            st.markdown("**Custom Tags:**")
            
            # For each custom tag, show name, color picker and delete button
            for i, tag in enumerate(custom_tags):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                # Tag name
                col1.write(f"• {tag}")
                
                # Color picker
                current_color = custom_colors.get('tags', {}).get(tag, "#808080")
                new_color = col2.color_picker(
                    "Color", 
                    current_color, 
                    key=f"color_picker_{tag}_{i}",
                    label_visibility="collapsed"
                )
                
                # Update color if changed
                if new_color != current_color:
                    if 'tags' not in custom_colors:
                        custom_colors['tags'] = {}
                    custom_colors['tags'][tag] = new_color
                    settings['custom_colors'] = custom_colors
                    get_store()['settings'] = settings
                    save_data(get_store())
                
                # Delete button
                if col3.button("🗑️", key=f"remove_tag_{i}", help=f"Remove {tag}"):
                    custom_tags.remove(tag)
                    if tag in custom_colors.get('tags', {}):
                        del custom_colors['tags'][tag]
                    
                    settings['custom_tags'] = custom_tags
                    settings['custom_colors'] = custom_colors
                    get_store()['settings'] = settings
                    save_data(get_store())
                    st.rerun()
        else:
            st.info("No custom tags yet. Add one above.")
        
        # Color customization section
        st.markdown("### Color Customization")
        
        # Add color mode toggle
        color_mode = settings.get('color_mode', DEFAULT_SETTINGS['color_mode'])
        new_color_mode = st.radio(
            "Node Color Mode",
            options=["Urgency", "Tag"],
            index=0 if color_mode == 'urgency' else 1,
            horizontal=True,
            help="Choose whether to color nodes based on urgency level or tag"
        )
        # Convert display name to config value
        new_color_mode = new_color_mode.lower()
        
        # Add explanation of current mode
        if new_color_mode == 'urgency':
            st.info("Nodes are colored by urgency level (high, medium, low).")
        else:
            st.info("Nodes are colored by their assigned tag. Nodes without tags will use urgency colors.")
        
        # Color tabs for urgency and tags
        color_tab1, color_tab2 = st.tabs(["Urgency Colors", "Tag Colors"])
        
        # Urgency color pickers
        with color_tab1:
            urgency_colors = custom_colors.get('urgency', DEFAULT_SETTINGS['custom_colors']['urgency'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                high_color = st.color_picker(
                    "High Urgency", 
                    urgency_colors.get('high', DEFAULT_SETTINGS['custom_colors']['urgency']['high']),
                    help="Color for high urgency nodes"
                )
            with col2:
                medium_color = st.color_picker(
                    "Medium Urgency", 
                    urgency_colors.get('medium', DEFAULT_SETTINGS['custom_colors']['urgency']['medium']),
                    help="Color for medium urgency nodes"
                )
            with col3:
                low_color = st.color_picker(
                    "Low Urgency", 
                    urgency_colors.get('low', DEFAULT_SETTINGS['custom_colors']['urgency']['low']),
                    help="Color for low urgency nodes"
                )
            
            # Update urgency colors if changed
            if (high_color != urgency_colors.get('high') or 
                medium_color != urgency_colors.get('medium') or 
                low_color != urgency_colors.get('low')):
                custom_colors['urgency'] = {
                    'high': high_color,
                    'medium': medium_color,
                    'low': low_color
                }
        
        # Tag color pickers
        with color_tab2:
            tag_colors = custom_colors.get('tags', DEFAULT_SETTINGS['custom_colors']['tags'])
            
            # Get all tags (built-in only)
            builtin_tags = list(TAGS.keys())
            
            st.markdown("#### Built-in Tags")
            
            # Create 2 columns for built-in tag colors
            tag_col1, tag_col2 = st.columns(2)
            
            half_length = len(builtin_tags) // 2 + len(builtin_tags) % 2
            
            # First column of built-in tags
            with tag_col1:
                for tag in builtin_tags[:half_length]:
                    tag_color = st.color_picker(
                        f"{tag.capitalize()}", 
                        tag_colors.get(tag, TAGS[tag]['color']),
                        help=f"Color for {tag} tag"
                    )
                    # Update if changed
                    if tag_color != tag_colors.get(tag):
                        tag_colors[tag] = tag_color
            
            # Second column of built-in tags
            with tag_col2:
                for tag in builtin_tags[half_length:]:
                    tag_color = st.color_picker(
                        f"{tag.capitalize()}", 
                        tag_colors.get(tag, TAGS[tag]['color']),
                        help=f"Color for {tag} tag"
                    )
                    # Update if changed
                    if tag_color != tag_colors.get(tag):
                        tag_colors[tag] = tag_color
            
            # Note about custom tags
            st.info("Custom tag colors can be changed in the Tag Management section above.")
            
            # Update tag colors
            custom_colors['tags'] = tag_colors
        
        # Save all settings if changed
        settings_changed = (
            edge_length != default_edge_length or 
            spring_strength != default_spring_strength or 
            size_multiplier != default_size_multiplier or
            new_color_mode != color_mode
        )
        
        if settings_changed:
            settings['edge_length'] = edge_length
            settings['spring_strength'] = spring_strength
            settings['size_multiplier'] = size_multiplier
            settings['color_mode'] = new_color_mode
            settings['custom_colors'] = custom_colors
            get_store()['settings'] = settings
            save_data(get_store()) 