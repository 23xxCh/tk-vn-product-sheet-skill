# Generated image URL contract

## Accepted value

The workbook may receive a generated-image value only when it is:

- a public `https://` URL
- fetchable without local filesystem access
- stable long enough for the listing workflow
- the final cleaned image, not an HTML preview page

## Rejected values

- local or relative paths
- bare filenames
- `file://` URLs
- `data:` URIs
- conversation-only attachments
- invented URLs

## Built-in image generation

The built-in image model can return a local temporary artifact in some runtimes.
That artifact is not a publishable URL. Use a user-authorized hosting connector
or uploader, receive its URL, verify it, then write it to the workbook.

If the runtime directly returns a public stable URL, verify it before use. If no
hosting path exists, report the blocker; do not silently fall back to local files.
