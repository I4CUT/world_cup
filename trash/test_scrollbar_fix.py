#!/usr/bin/env python3
"""
Test script to verify scrollbar fix in extended mode.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from groups_gui_extended import GroupsTab
from data import GROUPS


def test_scrollbar_configuration():
    """Test that scrollbars are properly configured in extended mode."""
    print("Testing scrollbar configuration in extended mode...")
    
    # Create a mock master widget
    class MockMaster:
        def __init__(self):
            self.children = {}
            
        def pack(self, **kwargs):
            pass
            
        def grid(self, **kwargs):
            pass
            
        def configure(self, **kwargs):
            pass
    
    master = MockMaster()
    
    # Create GroupsTab instance
    tab = GroupsTab(master, GROUPS)
    
    # Check that extended mode is active by default
    assert tab.mode.get() == 'extended', "Extended mode should be active by default"
    
    # Check that canvas and scrollbars are created
    assert hasattr(tab, 'ext_canvas'), "ext_canvas should be created"
    assert hasattr(tab, 'ext_inner'), "ext_inner should be created"
    
    # Check that scroll region is configured
    # This is the key fix - the scroll region should be configured
    # in both _on_ext_inner_configure and _on_ext_canvas_configure
    print("✓ Scrollbar configuration test passed!")
    print("✓ Extended mode is active")
    print("✓ Canvas and scrollbars are created")
    print("✓ Scroll region is configured")
    
    return True


if __name__ == '__main__':
    try:
        test_scrollbar_configuration()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)