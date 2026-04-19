## MediaLens v1.1.26

### Summary

This release makes local AI support more reliable and ready for future model expansion. Gemma 4, InternLM XComposer2, and WD SwinV2 can now run through separate model workers so one model's requirements are much less likely to disrupt another.

### Highlights

- Use Gemma 4, InternLM XComposer2, and WD SwinV2 side by side with cleaner separation behind the scenes.
- See whether local AI models are installed from the new Local AI Models setup window or from AI settings, and install missing model support from either place.
- Install local AI support without separately installing Python first; MediaLens now prepares its own Python bootstrap as needed.
- Write description prompts with more control: tags are only included when `{tags}` is used, and starter text is handled as a model instruction.
- Get clearer local AI progress and error feedback during long-running generation.

### Notes

- Local AI models are now structured around separate worker subprocesses and optional per-model runtimes, which gives MediaLens a safer path for adding more models over time.
- Model dependencies and model weights are not bundled into the main installer. They are installed only when selected in the Local AI Models setup window or AI settings.
- Full changelog: <https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
