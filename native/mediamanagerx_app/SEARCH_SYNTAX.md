# Search Syntax Help

Search is case-insensitive.

## Basic Rules

- Separate terms with spaces to require all of them.
- Use quotes for exact phrases.
- Use `OR` or `|` to match either side.
- Prefix a term with `-` to exclude it.
- Prefix a term with `+` to make intent explicit for a required term.
- Use `*` and `?` as wildcards.

## Examples

- `red hair portrait`
- `"grand canyon"`
- `vegas OR arizona`
- `portrait -blurry`
- `tag:favorite collection:vacation`
- `file:*.png`

## Field Search

Use `field:value` to search a specific field.

Supported text fields:

- `path`
- `file` or `filename`
- `folder`
- `title`
- `description` or `desc`
- `notes`
- `tag` or `tags`
- `collection` or `collections`
- `prompt`
- `negative` or `negprompt`
- `tool`
- `model`
- `checkpoint`
- `sampler`
- `scheduler`
- `source`
- `family`
- `lora`
- `type`
- `ext`

Supported date fields:

- `date-taken` or `exif-date-taken`
- `date-acquired` or `metadata-date`
- `original-file-date`
- `date-created` or `file-created-date`
- `date-modified` or `file-modified-date`

Examples:

- `collection:vacation`
- `folder:animals`
- `model:flux`
- `prompt:"red dress"`
- `ext:png`
- `date-modified:>=2026-05-20`
- `date-taken:=2026-05-20`

## Numeric Search

Use `>`, `>=`, `<`, `<=`, or `=` with numeric fields.

Supported numeric fields:

- `cfg`
- `steps`
- `seed`
- `width`
- `height`
- `duration`
- `size`

Examples:

- `cfg:10`
- `steps:<5`
- `steps>=20`
- `width:>=1024`
- `duration:<10s`
- `size:>5mb`

## Notes

- Collection names are searchable, so media can match through collection membership even if the collection name is not in the file name, folder, tags, or description.
- `duration` supports `ms`, `s`, `m`, and `h`.
- `size` supports `b`, `kb`, `mb`, `gb`, and `tb`.
