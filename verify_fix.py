from pathlib import Path

def filter_logic(path_str, root_path):
    try:
        # Normalize for robust comparison (lowercase posix)
        p_str = Path(path_str).as_posix().lower()
        r_str = Path(root_path).as_posix().lower()
        
        # Case 1: Root itself
        if p_str == r_str:
            return True
            
        # Case 2: p is an ancestor of r
        p_prefix = p_str if p_str.endswith("/") else p_str + "/"
        if r_str.startswith(p_prefix):
            return True
            
        # Case 3: p is a descendant of r
        r_prefix = r_str if r_str.endswith("/") else r_str + "/"
        if p_str.startswith(r_prefix):
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
    ("C:", True, "Ancestor (Drive letter)"),
    ("C:\\", True, "Ancestor (Drive root)"),
    ("C:\\Users", False, "External sibling in User dir"),
    ("C:\\Other_Folder", False, "External sibling"),
    ("C:\\My_Media_Longer", False, "Partial name match (should fail)"),
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
