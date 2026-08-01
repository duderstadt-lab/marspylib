import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "marspylib"
copyright = "2018-2026, Duderstadt Lab"
author = "Karl Duderstadt, Nadia Huisjes, Thomas Retzer"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_typehints = "description"
autodoc_member_order = "bysource"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_heading_anchors = 3

html_theme = "furo"
html_title = "marspylib"
