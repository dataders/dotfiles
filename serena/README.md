# Serena per-repo config

Serena writes a `.serena/` dir into every repo it works in. `.serena/` is
globally gitignored, so it never pollutes a repo. The per-repo **truth** lives
here and is symlinked back into each repo:

```
serena/projects/<repo>/
    project.yml   # minimal stub (project_name + languages); rest inherited
    memories/     # Serena's notes; fills up over time
```

`<repo>/.serena/project.yml` and `<repo>/.serena/memories/` are symlinks into
this tree (via `links.tsv`), so Serena's writes land here as committable files.
`cache/` is never tracked.

Register a repo with `bin/serena-link <repo-path>`, then run `./links.sh apply`
from the primary checkout. The dotfiles repo itself is special-cased: its own
`.serena/project.yml` is tracked in place with no symlink.
