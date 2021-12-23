# flake8-ls: super fast flake8 language server

Its preload flake8 and its plugins only once.

It supports diagnostics only.

## Status

It works but plugins are loaded when the language server start. So if you use
the same langauge for files from different projects, you may have trouble if
they configuration/plugins are not indentic. That the compromise to be so fast.

## Install

```shell
$ pip install --user flake8-ls
```

## vim-lspconfig

```lua
lua << EOF
require("lspconfig.configs")["flake8ls"] = {
    default_config = {
        cmd = { 'flake8-ls' },
        filetypes = { 'python' },
        root_dir = lspconfig.util.root_pattern('pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', 'Pipfile'),
        single_file_support = true,
    },
}
require("lspconfip").flake8ls.setup({})
EOF
```
