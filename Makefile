SPHINXBUILD ?= sphinx-build
SOURCEDIR = docs
BUILDDIR = docs/_build
 
.PHONY: help html clean
 
help:
    @$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)"
 
html:
    $(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html"
 
clean:
    rm -rf "$(BUILDDIR)"