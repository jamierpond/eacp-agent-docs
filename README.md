# eacp-agent-docs

Builds a markdown API reference for coding agents from a C++ library's headers,
and publishes it to a Google Cloud Storage bucket from GitHub Actions. Each
header gets a page of its types, public members, doc comments and the example
files that use it; each module gets an index and a symbol list; the root gets
`index.md`, `symbols.md` and an `llms.txt`. Every page is also rendered to
HTML beside it. All links are relative, so the tree works under any prefix.

## Use it in a repository

Add `agent-docs.toml` at the repository root and this workflow:

```yaml
name: Agent docs
on:
  push:
    branches: [main, develop]
    tags: ["v*"]
  workflow_dispatch:
jobs:
  publish:
    permissions:
      contents: read
      id-token: write
    uses: jamierpond/eacp-agent-docs/.github/workflows/publish.yml@v1
    with:
      workload_identity_provider: ${{ vars.AGENT_DOCS_WORKLOAD_IDENTITY_PROVIDER }}
      service_account: ${{ vars.AGENT_DOCS_SERVICE_ACCOUNT }}
      bucket: ${{ vars.AGENT_DOCS_BUCKET }}
```

The repository must be listed in the identity provider (see "Bucket and
identity" below) and have those three Actions variables set.

To build locally (needs Doxygen and `pip install -r requirements.txt`):

```bash
python3 path/to/eacp-agent-docs/scripts/generate.py --config agent-docs.toml
python3 path/to/eacp-agent-docs/scripts/check-links.py build/agent-docs
```

## agent-docs.toml

```toml
name = "Miro"                 # page titles
slug = "miro"                 # bucket folder; default name
summary = "One sentence for llms.txt."
source_url = "https://github.com/owner/repo/blob/develop/"   # "Used in" and guide links
include_root = "Lib"          # include paths are relative to this
header_roots = ["Lib/Miro"]   # what Doxygen reads
namespace_dir = "Miro"        # first include path segment; default name
namespace = "Miro"            # C++ prefix dropped from symbol names; default namespace_dir
root_module = "Miro"          # module for headers directly in namespace_dir; default namespace_dir
exclude_patterns = ["*/Detail/*"]        # Doxygen EXCLUDE_PATTERNS
exclude_symbols = ["*::Detail::*"]       # Doxygen EXCLUDE_SYMBOLS
hidden_namespace_parts = ["Detail", "detail", "Impl", "Test"]   # the default
internal_marker = "Internal:" # a header whose @file starts with it gets no page
tasks_file = "Docs/Tasks.md"  # optional "| task | symbol |" table
getting_started_file = "Docs/GettingStarted.md"   # optional, copied to getting-started.md
examples_dirs = ["Examples"]  # searched for "Used in" links
index_links = [{ label = "Reuse map", path = "Docs/Toolbox.md" }]

[external_repositories]       # task-table symbols outside this library
Other = "https://github.com/owner/other"

[doxygen]
file_patterns = ["*.h", "*.dox"]   # the default
predefined = []

[platforms]                   # all optional; a "Platform:" line on pages
file_suffixes = ["Windows", "Linux"]        # Foo-Windows.cpp is platform-only
directories = { Windows = "Windows" }       # headers under a Windows/ folder
modules = { Core = "every platform" }       # line on a module index
[[platforms.path_gates]]                    # headers matching a regex
pattern = 'Miro/Win/.*'
platforms = "Windows"
[[platforms.header_gates]]                  # same, several patterns, one label
platforms = "Apple and Windows"
patterns = ['Miro/A\.h', 'Miro/B\.h']
```

A module is the first folder under `namespace_dir`. Its preamble is the
`@file` block of its umbrella header (`<Module>/<Module>.h` or `<Module>/<namespace_dir><Module>.h`, any case), or a `@dir`
block in a `.dox` file. `DocCommentStyle.md` is how to write the comments.

## Where it publishes

`gs://<bucket>/<slug>/<ref>/`, where the refs of one run are:

- always the 7-character commit sha, never rewritten once it exists;
- on a tag push, also the tag, never rewritten;
- on a push to the default branch, `latest` and the branch name;
- on a push to `main`, `main` and `stable` (and `latest` if `main` is the default).
- on a push to any other branch, its name with `/` turned into `-`.

The named folders are replaced wholesale on every publish and served with a
5-minute cache.

## Bucket and identity

`scripts/setup-gcp.sh <gcp-project> <bucket> <owner/repo>...` creates or
updates the public-read bucket, a service account that can write only to it,
and a Workload Identity Federation provider that accepts GitHub Actions tokens
from exactly the repositories listed. Pass every caller each time. It prints
the three variables to set on each calling repository.
