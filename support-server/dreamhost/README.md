# MediaLens DreamHost Debug Log Submission

This folder contains a small PHP endpoint for receiving sanitized MediaLens debugging-log zip bundles.

## What I Need From You

1. Create a DreamHost subdomain, such as `medialens.glenbland.com`.
2. Enable HTTPS/Let's Encrypt for that subdomain.
3. Confirm the subdomain's web directory path in DreamHost panel.
4. Choose a support email address that should receive report notifications.
5. Generate a long random upload token. Example PowerShell:

   ```powershell
   [Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
   ```

6. Tell me the final HTTPS endpoint URL, for example:

   ```text
   https://medialens.glenbland.com/api/submit-debug-log.php
   ```

Do not send me your DreamHost password. If you want me to prepare exact files, the endpoint URL and chosen token are enough.

## Manual Deployment

1. In the subdomain web directory, create an `api` folder.
2. Upload `submit-debug-log.php` into that `api` folder.
3. Edit the top of `submit-debug-log.php`:

   ```php
   const SUPPORT_EMAIL = 'your-email@example.com';
   const SHARED_TOKEN = 'your-long-random-secret';
   ```

4. Visit the endpoint in a browser. A healthy deployment should return JSON saying `POST required`.
5. Configure MediaLens with:

   ```powershell
   $env:MEDIALENS_DEBUG_UPLOAD_URL = 'https://medialens.glenbland.com/api/submit-debug-log.php'
   $env:MEDIALENS_DEBUG_UPLOAD_TOKEN = 'your-long-random-secret'
   ```

For a release build, the app can store those as hidden settings instead of environment variables.

## Storage

The PHP script stores uploaded zip files outside the web root by default:

```text
<account-home>/medialens-debug-uploads/bundles/
<account-home>/medialens-debug-uploads/index.jsonl
```

That keeps uploaded reports from being directly downloadable by URL.

## Retention

Until there is an automated purge job, periodically delete old files from:

```text
medialens-debug-uploads/bundles/
```

Recommended retention for early beta support: 14 to 30 days.

## Privacy

MediaLens creates the zip bundle locally and excludes:

- media files
- thumbnails
- recycle-bin files
- settings
- databases

The app also redacts path-like values where practical before the bundle is created. The endpoint still treats uploads as private support data.

