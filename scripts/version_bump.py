import sys
import re
from pathlib import Path

def bump_version(current_version, arg=None):
    if arg:
        return arg.lstrip('v')
    
    parts = list(map(int, current_version.lstrip('v').split('.')))
    if len(parts) < 3:
        parts.extend([0] * (3 - len(parts)))
    parts[2] += 1
    return '.'.join(map(str, parts))

def update_file(path, pattern, replacement):
    if not path.exists():
        print(f"Warning: {path} not found.")
        return False
    
    content = path.read_text(encoding='utf-8')
    new_content = re.sub(pattern, replacement, content)
    
    if content != new_content:
        path.write_text(new_content, encoding='utf-8')
        print(f"Updated {path}")
        return True
    else:
        print(f"No changes needed for {path}")
        return False

def main():
    root = Path(__file__).parent.parent
    version_file = root / "VERSION"
    
    if not version_file.exists():
        print("Error: VERSION file not found in root.")
        sys.exit(1)
    
    current_version = version_file.read_text(encoding='utf-8').strip().lstrip('v')
    
    new_version_arg = sys.argv[1] if len(sys.argv) > 1 else None
    new_version = bump_version(current_version, new_version_arg)
    
    print(f"Bumping version: {current_version} -> {new_version}")
    
    # 1. VERSION
    version_file.write_text(f"v{new_version}\n", encoding='utf-8')
    print(f"Updated VERSION to v{new_version}")
    
    # 2. native/mediamanagerx_app/main.py
    main_py = root / "native" / "mediamanagerx_app" / "main.py"
    update_file(main_py, r'__version__ = "v[\d.]+"', f'__version__ = "v{new_version}"')

    # 2b. native/mediamanagerx_app/common.py
    common_py = root / "native" / "mediamanagerx_app" / "common.py"
    update_file(common_py, r'__version__ = "v[\d.]+"', f'__version__ = "v{new_version}"')
    
    # 3. installer.iss
    iss = root / "installer.iss"
    update_file(iss, r'#define MyAppVersion "v[\d.]+"', f'#define MyAppVersion "v{new_version}"')
    
    # 4. pyproject.toml
    toml = root / "pyproject.toml"
    update_file(toml, r'version = "[\d.]+"', f'version = "{new_version}"')

    # 5. setup.cfg
    setup_cfg = root / "setup.cfg"
    update_file(setup_cfg, r"version = [\d.]+", f"version = {new_version}")

if __name__ == "__main__":
    main()
