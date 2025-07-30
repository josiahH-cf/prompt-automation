#!/usr/bin/env python3
"""Test script to verify the consolidation changes work correctly."""

import sys
from pathlib import Path

def test_consolidation():
    print("🧪 Testing prompt-automation consolidation...")
    
    # Add src to path
    sys.path.insert(0, 'src')
    
    try:
        # Test core imports (avoiding paste.py which needs pyperclip)
        print("✅ Testing core imports...")
        from prompt_automation.menus import PROMPTS_DIR, list_styles
        from prompt_automation.renderer import load_template
        from prompt_automation.variables import get_variables
        from prompt_automation.logger import log_usage
        
        # Test path resolution
        print(f"✅ PROMPTS_DIR resolves to: {PROMPTS_DIR}")
        print(f"✅ PROMPTS_DIR exists: {PROMPTS_DIR.exists()}")
        
        if PROMPTS_DIR.exists():
            styles = list_styles()
            print(f"✅ Available styles: {styles}")
            
            # Test loading a template
            if styles:
                first_style = styles[0]
                prompts = list((PROMPTS_DIR / first_style).glob("*.json"))
                if prompts:
                    template = load_template(prompts[0])
                    print(f"✅ Successfully loaded template: {template['title']}")
                else:
                    print("⚠️  No prompts found in first style")
            else:
                print("⚠️  No styles found")
        else:
            print("❌ PROMPTS_DIR does not exist")
            return False
            
        print("🎉 All consolidation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_consolidation()
    sys.exit(0 if success else 1)
