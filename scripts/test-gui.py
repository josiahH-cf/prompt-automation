#!/usr/bin/env python3
"""
Quick test script to verify the prompt-automation GUI workflow works.
This can be run manually to test the installation.
"""

import sys
import os
from pathlib import Path

# Add src to path if running from source
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import tkinter as tk
        print("✓ tkinter imported successfully")
    except ImportError as e:
        print(f"✗ tkinter import failed: {e}")
        return False
    
    try:
        import prompt_automation.gui
        from prompt_automation.gui.controller import PromptGUI
        print("✓ prompt_automation.gui imported successfully")
        print("✓ PromptGUI imported successfully")
    except ImportError as e:
        print(f"✗ prompt_automation.gui import failed: {e}")
        return False
    
    try:
        import prompt_automation.menus
        print("✓ prompt_automation.menus imported successfully")
    except ImportError as e:
        print(f"✗ prompt_automation.menus import failed: {e}")
        return False
    
    return True

def test_templates():
    """Test that templates can be found and loaded."""
    print("\nTesting template discovery...")
    
    try:
        import prompt_automation.menus as menus
        
        styles = menus.list_styles()
        if not styles:
            print("✗ No template styles found")
            return False
        
        print(f"✓ Found {len(styles)} style(s): {', '.join(styles)}")
        
        total_templates = 0
        for style in styles:
            prompts = menus.list_prompts(style)
            print(f"  - {style}: {len(prompts)} template(s)")
            total_templates += len(prompts)
            
            # Test loading first template
            if prompts:
                try:
                    template = menus.load_template(prompts[0])
                    title = template.get('title', 'Unknown')
                    placeholders = len(template.get('placeholders', []))
                    print(f"    ✓ Loaded '{title}' with {placeholders} placeholder(s)")
                except Exception as e:
                    print(f"    ✗ Failed to load template: {e}")
                    return False
        
        if total_templates == 0:
            print("✗ No templates found in any style")
            return False
        
        print(f"✓ Template loading works ({total_templates} total templates)")
        return True
        
    except Exception as e:
        print(f"✗ Template test failed: {e}")
        return False

def test_gui_creation():
    """Test that GUI windows can be created (but don't show them)."""
    print("\nTesting GUI creation...")
    
    try:
        import tkinter as tk
        
        # Test basic window creation
        root = tk.Tk()
        root.withdraw()  # Hide the window
        root.destroy()
        print("✓ Basic Tkinter window creation works")
        
        # Test with our GUI components
        root = tk.Tk()
        root.withdraw()
        
        # Test listbox
        listbox = tk.Listbox(root)
        listbox.insert("end", "Test item")
        
        # Test text widget  
        text = tk.Text(root)
        text.insert("1.0", "Test text")
        
        # Test entry
        entry = tk.Entry(root)
        entry.insert(0, "Test entry")
        
        root.destroy()
        print("✓ GUI widget creation works")
        
        return True
        
    except Exception as e:
        print(f"✗ GUI creation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Prompt Automation GUI Test ===\n")
    
    tests = [
        ("Module imports", test_imports),
        ("Template discovery", test_templates), 
        ("GUI creation", test_gui_creation),
    ]
    
    passed = 0
    for name, test_func in tests:
        print(f"Running {name} test...")
        if test_func():
            passed += 1
            print(f"✓ {name} test PASSED\n")
        else:
            print(f"✗ {name} test FAILED\n")
    
    print("=== Test Summary ===")
    print(f"Passed: {passed}/{len(tests)} tests")
    
    if passed == len(tests):
        print("🎉 All tests passed! GUI should work correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
