import os
import shutil
from pathlib import Path

def filter_logic(path_str, root_path):
    # Mimic RootFilterProxyModel logic
    item_p = Path(path_str).resolve()
    root_p = Path(root_path).resolve()
    
    item_p_str = str(item_p).lower()
    root_p_str = str(root_p).lower()
    root_parents_lower = [str(p).lower() for p in root_p.parents]
    item_parents_lower = [str(p).lower() for p in item_p.parents]
    
    print(f"Checking: {path_str}")
    print(f"  Resolved item: {item_p}")
    print(f"  Resolved root: {root_p}")
    
    if item_p_str == root_p_str:
        return True
    if root_p_str in item_parents_lower:
        return True
    if item_p_str in root_parents_lower:
        return True
    return False

# Setup test environment
test_root = Path("test_root").absolute()
test_root.mkdir(exist_ok=True)
external_folder = Path("external_folder").absolute()
external_folder.mkdir(exist_ok=True)

symlink_path = test_root / "my_symlink"
if os.path.exists(symlink_path):
    os.remove(symlink_path)

try:
    # Create symlink (might need admin on Windows, but let's try)
    os.symlink(external_folder, symlink_path, target_is_directory=True)
    print(f"Created symlink {symlink_path} -> {external_folder}")
except Exception as e:
    print(f"Failed to create symlink: {e}")
    # Fallback to juntao or similar if needed, but on Windows 10+ devs usually have symlink privs
    exit(1)

# Test the logic
is_accepted = filter_logic(str(symlink_path), str(test_root))
print(f"Accepted: {is_accepted}")

if not is_accepted:
    print("BUG REPRODUCED: Symlink pointing outside root is filtered out.")
else:
    print("Bug not reproduced with this logic.")

# Clean up
os.remove(symlink_path)
test_root.rmdir()
external_folder.rmdir()
