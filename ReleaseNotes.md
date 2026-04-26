## MediaLens v1.2.3

### Summary

This release protects Fast OCR setups that are already using the GPU. Paddle OCR repair now avoids downgrading a working GPU runtime to CPU fallback and reports repair problems more accurately.

### Highlights

- Fast OCR repair keeps an active Paddle GPU runtime in place instead of removing it before repair is proven safe.
- Failed Paddle OCR repairs now re-check the runtime so MediaLens does not incorrectly show a working install as missing.
- CPU fallback setup now tries the package source that works for current Paddle CPU wheels first.

### Notes

- No bundled local AI runtime packages were added to the installer; Paddle OCR still uses the managed per-user runtime under AppData.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
