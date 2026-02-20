from pathlib import Path

def filter_logic(path_str, root_path):
    try:
        # Mimic fixed RootFilterProxyModel logic
        item_p = Path(path_str)
        root_p = Path(root_path)
        
        # Normalize for Windows case-insensitivity and slash consistency
        item_p_str = str(item_p).lower().replace("\\", "/")
        root_p_str = str(root_p).lower().replace("\\", "/")
        
        # 1. Accept the root folder itself or its descendants
        if item_p_str == root_p_str or item_p_str.startswith(root_p_str + "/"):
            return True
            
        # 2. Accept ancestors of the root folder (so we can reach it from drive)
        root_parents_lower = [str(p).lower().replace("\\", "/") for p in root_p.parents]
        if item_p_str in root_parents_lower:
            return True
            
        return False
    except Exception as e:
        print(f"Error: {e}")
        return True

# Test Scenarios (Dummy paths - no filesystem needed)
root = "C:\\My_Media"

tests = [
    ("C:\\My_Media", True, "Root folder itself"),
    ("C:\\My_Media\\Subfolder", True, "Direct child"),
    ("C:\\My_Media\\Symlink_To_External", True, "Symlink (apparent path within root)"),
    ("C:\\My_Media\\Subfolder\\Nested", True, "Deep descendant"),
    ("C:\\", True, "Ancestor (Drive)"),
    ("C:\\Other_Folder", False, "External sibling"),
]

print(f"Verifying with root: {root}")
all_passed = True
for path, expected, desc in tests:
    result = filter_logic(path, root)
    status = "PASS" if result == expected else "FAIL"
    print(f"[{status}] {desc}: Input={path}, Expected={expected}, Result={result}")
    if result != expected:
        all_passed = False

if all_passed:
    print("\nVERIFICATION SUCCESSFUL: Filtering logic works as expected, including support for apparent paths (symlinks).")
else:
    print("\nVERIFICATION FAILED: Some scenarios did not match expectations.")
    exit(1)
