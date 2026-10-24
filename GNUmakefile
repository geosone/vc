# The Volkov Commander 4.99.10 alpha with JWasm and JWlink.
#
#   make                 build/VC.COM, build/VC.OVL
#   make release         build/release/ and build/vc49910a.zip: the program,
#                        the files of files/, compiled XML help
#                        the GeosOne Dual Installer and downloaded DOS packers
#   make disk            build/vc49910a.img, core-only 1.44 MB installation disk
#   make port            the published TASM sources converted again by
#                        tools/tasm2jwasm.py to build/port/, compared to src/
#   make clean
#
# JWASM, JWLINK: the programs; GDI: the directory of INSTALL.EXE (and
# gdicheck) of https://github.com/geosone/gdi.

JWASM   ?= jwasm
JWLINK  ?= $(or $(shell command -v jwlink 2>/dev/null),$(firstword $(wildcard ../jwlink-fork/build/jwlinkLR/jwlink)),jwlink)
GDI     ?= ../gdi/build
PYTHON  ?= python3
WATCOM  ?= /opt/watcom
WCL     ?= $(WATCOM)/binl64/wcl
CC      ?= cc
PACKER_CACHE ?= $(B)/downloads

B       := build
REL     := $(B)/release
NAME    := vc49910a
SOURCES := $(wildcard src/*.ASM src/*.INC)
FILES   := $(shell cd files && find . -type f | sed 's|^\./||' | sort)
HELP_NAMES := VC.HLP VC-GER.HLP VCR.HLP VC-PL.HLP VC-SK.HLP
HELPS   := $(addprefix $(B)/help/,$(HELP_NAMES))
HELP_MAP := $(B)/help/VCHELPMAP.INC
HELP_SOURCES := help/project.xml help/project.dtd help/guide.dtd $(wildcard help/src/*.xml)
ASSET_NAMES := $(shell $(PYTHON) tools/assets.py list)
ASSETS := $(addprefix $(B)/assets/,$(ASSET_NAMES))
ASSET_SOURCES := $(wildcard assets/*.xml assets/*.svg assets/*.dtd) tools/assets.py

# the published sources (the converter's input) and the LOOP/JCXZ lines
# TASM's JUMPS had to extend there (tools/tasm2jwasm.py -x)
SRCURL  := https://vc.vvv.kyiv.ua/download/src/vc49909.zip
SRCSHA  := b70fda9f9c94a321681dc49828f99ff4abe2c2f741e85c5bffab7ab6310b9f93
FAR     := VCARC2.INC:1188 VCDIALOG.INC:1921 VCMEM.INC:536 VCMENU.INC:631 \
           VCPANELS.INC:1601 VCPANELS.INC:1865 VCPANELS.INC:2123 VCVIEW.INC:1728

.PHONY: all release disk check test help assets addons packers port clean

all: $(B)/VC.COM $(B)/VC.OVL addons assets

help: $(HELPS) $(HELP_MAP) $(B)/help/manifest.xml

# One invocation produces every language and their shared context table.
# Grouped targets also regenerate the set if one output is removed.
$(HELPS) $(HELP_MAP) $(B)/help/manifest.xml &: $(HELP_SOURCES) src/VCDATA.INC tools/hlp.py | $(B)
	$(PYTHON) tools/hlp.py build --output $(B)/help

assets: $(ASSETS) $(B)/assets/manifest.xml

$(ASSETS) $(B)/assets/manifest.xml &: $(ASSET_SOURCES) | $(B)
	$(PYTHON) tools/assets.py build --output $(B)/assets

addons: $(B)/VCTOOLS.EXE $(B)/VC7Z.EXE

$(B)/VCTOOLS.EXE: addons/vctools.c | $(B)
	WATCOM="$(WATCOM)" INCLUDE="$(WATCOM)/h" PATH="$(WATCOM)/binl64:$$PATH" $(WCL) -q -bt=dos -0 -ms -os -w4 -we -fe=$@ -fo=$(B)/vctools.obj $<

$(B)/VC7Z.EXE: addons/vc7z.c | $(B)
	WATCOM="$(WATCOM)" INCLUDE="$(WATCOM)/h" PATH="$(WATCOM)/binl64:$$PATH" $(WCL) -q -bt=dos -0 -ms -os -k8192 -w4 -we -fe=$@ -fo=$(B)/vc7z.obj $<

$(B)/vctools-host: addons/vctools.c | $(B)
	$(CC) -std=c89 -Wall -Wextra -Werror -O2 -o $@ $<

$(B)/vc7z-host: addons/vc7z.c | $(B)
	$(CC) -std=c89 -Wall -Wextra -Werror -O2 -o $@ $<

$(B)/ADDONS.TXT: addons/README.de.md | $(B)
	$(PYTHON) -c 'from pathlib import Path; p=Path("$<"); s=p.read_text().replace("„", "\"").replace("“", "\"").replace("…", "..."); Path("$@").write_bytes(s.replace("\n", "\r\n").encode("cp850"))'

test: help assets $(B)/vctools-host $(B)/vc7z-host
	VCTOOLS=$(CURDIR)/$(B)/vctools-host VC7Z=$(CURDIR)/$(B)/vc7z-host $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

$(B):
	mkdir -p $@

$(B)/%.obj: src/%.ASM $(SOURCES) $(HELP_MAP) | $(B)
	cd src && $(JWASM) -q -c -DOFFICIAL -Fo=../$@ $(notdir $<)

# VC.COM: the resident part (tiny model), VC.OVL: the program (an EXE)
$(B)/VC.COM: $(B)/VC.obj
	$(JWLINK) format dos com file $< name $@ option quiet </dev/null

$(B)/VC.OVL: $(B)/VCOVL.obj
	$(JWLINK) format dos file $< name $@ option quiet </dev/null

release: $(B)/$(NAME).zip

# Verification also runs on a warm cache, so a corrupt download cannot be reused.
packers: downloads.txt tools/packers.py install/INSTALL.INI | $(B)
	$(PYTHON) tools/packers.py --cache "$(PACKER_CACHE)" --output $(B)/packers

define stage_core
	mkdir -p $(1)
	cp -r files/. $(1)/
	cd $(B)/assets && cp --parents $(ASSET_NAMES) $(abspath $(1))/
	cp $(HELPS) $(1)/
	cp $(B)/VC.COM $(B)/VC.OVL $(B)/VCTOOLS.EXE $(B)/VC7Z.EXE $(B)/ADDONS.TXT src/LICENSE.TXT install/INSTALL.INI $(GDI)/INSTALL.EXE $(1)/
endef

$(B)/$(NAME).zip: all packers $(B)/ADDONS.TXT install/INSTALL.INI src/LICENSE.TXT $(addprefix files/,$(FILES)) $(HELPS) $(ASSETS)
	rm -rf $(REL) $@
	$(call stage_core,$(REL))
	cp -r $(B)/packers/. $(REL)/
	cd $(REL) && zip -q -X -r ../$(NAME).zip .

check: release
	cd $(REL) && ../../$(GDI)/gdicheck INSTALL.INI

disk: $(B)/$(NAME).img

# Keep the 1.44 MB floppy usable on older machines; the full download bundle
# (including Retro7Zip source) belongs to the ZIP/directory release.
$(B)/$(NAME).img: all $(B)/ADDONS.TXT install/INSTALL.INI src/LICENSE.TXT $(addprefix files/,$(FILES)) $(HELPS) $(ASSETS)
	rm -rf $(B)/floppy
	$(call stage_core,$(B)/floppy)
	rm -f $@
	mformat -C -f 1440 -v VC49910A -i $@ ::
	cd $(B)/floppy && mcopy -s -i ../$(NAME).img * ::

$(B)/vc49909.zip: | $(B)
	curl -sSfL -o $@.tmp $(SRCURL)
	echo "$(SRCSHA)  $@.tmp" | sha256sum -c --quiet
	mv $@.tmp $@

port: $(B)/vc49909.zip
	rm -rf $(B)/published $(B)/port
	mkdir -p $(B)/published
	cd $(B)/published && unzip -q ../vc49909.zip
	$(PYTHON) -I tools/tasm2jwasm.py $(addprefix -x ,$(FAR)) $(B)/published $(B)/port
	-diff -r --exclude=*.TXT --exclude=*.EXT --exclude=MAKE.BAT $(B)/port src

clean:
	rm -rf $(B)
