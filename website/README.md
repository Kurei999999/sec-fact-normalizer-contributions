# Dataset download website

A buildless HTML/CSS/JavaScript site for GitHub Pages. Database binaries are hosted on Cloudflare R2, outside this directory and Git history.

## Preview locally

From the repository root:

```bash
python tools/build_website.py
python -m http.server 8000 --directory _site
```

Open http://localhost:8000. You can also open `website/index.html` directly: its generated `mapping-trees.js` bundle supports dropdowns and tree downloads without a local server. The SQL copy button works on HTTPS and localhost, with a manual-copy fallback.

## Publish the website

In GitHub repository **Settings → Pages → Build and deployment**, select **GitHub Actions**. Push the website and `.github/workflows/pages.yml` to `main`, or run **Deploy website** manually in Actions.

Expected URL: https://kurei999999.github.io/sec-fact-normalizer-contributions/

## Publish a database

1. Finish and validate a closed database snapshot.
2. Compress it and upload it to your R2 bucket.
3. Update the download URL, file name, upload date, and size in `website/index.html`. Metadata is explicit, not fetched from R2. The link works without JavaScript or CORS configuration.
4. Rebuild and deploy the website.

Current file: https://pub-5ff98667cdf0492596444bf0af58dd08.r2.dev/api_all_periods.sqlite3.gz

The `r2.dev` endpoint is rate-limited and intended for development. Replace it with your R2 custom-domain URL for production. Dataset licensing remains undecided. No credentials belong in website files.

The SQL example matches the upstream export schema: CIK is zero-padded text and financial values are decimal text.

## Automatic mapping trees

The Pages workflow rebuilds when `archetypes/**`, website files, or tree build tools change on `main`. `tools/build_website.py` renders the current JSON mappings with the same renderer as the repository text trees and packages them in ignored `_site/`. The browser’s industry and statement options come from the generated JavaScript bundle; no manual list is maintained. Rebuild locally after editing mappings.

`website/mapping-trees.js` is a generated preview bundle. Do not edit it manually; run `python tools/build_website.py` after mapping changes. Deployment regenerates it before packaging, so the hosted trees always match that deployment’s mappings.
