# dbt Fusion LSP (LSP4IJ custom template)

Points LSP4IJ at the released `dbt` binary (`~/.local/bin/dbt`), running
`dbt lsp --project-dir $PROJECT_DIR$`.

## Install

1. Install the LSP4IJ plugin (`com.redhat.devtools.lsp4ij`) if not already
   installed: `Settings > Plugins > Marketplace > search "LSP4IJ" > Install`.
2. Open the dbt project (e.g. jaffle-sandbox, internal-analytics) as the
   PyCharm project root — `$PROJECT_DIR$` must resolve to the directory
   containing `dbt_project.yml`.
3. `Settings > Languages & Frameworks > Language Servers > +`
4. In the "New Language Server" dialog, open the **Template** dropdown >
   **Import from custom template...** > select this directory
   (`~/Developer/dotfiles/.ide/lsp4ij-templates/dbt-fusion-lsp`).
5. Click OK. Open a `.sql` or `.yml` file in the project to start the server.

## Notes

- The binary path in `template.json` is the released `dbt` (2.x ships
  `dbt lsp`). To test an unreleased build, point it at that build's
  `target/debug/dbt` instead.
- `settings.json` mirrors the `dbt.lsp.*` settings shape the server pulls
  via `workspace/configuration` (see `crates/dbt-lsp/src/lsp_client_config.rs`
  and the Neovim integration at
  `crates/dbt-lsp/editor-integrations/neovim/dbt.lua`).
- Custom commands (`dbt.previewModel`, `dbt.previewCte`, `dbt.show`,
  `dbt.listNodes`, etc.) aren't wired to any PyCharm UI by this template —
  LSP4IJ's generic client doesn't provide per-server custom-command
  affordances the way the VS Code extension or Neovim integration do. Core
  LSP features (diagnostics, hover, go-to-definition, completion, rename,
  document symbols) should work out of the box.
