# The Volkov Commander 4.99.10 alpha with JWasm and JWlink.
#
#   make                 build/VC.COM, build/VC.OVL
#   make release         build/release/ and build/vc49910a.zip: the program,
#                        the files of files/, the help files of help/
#                        and the GeosOne Dual Installer
#   make disk            build/vc49910a.img, a 1.44 MB disk of the release
#   make port            the published TASM sources converted again by
#                        tools/tasm2jwasm.py to build/port/, compared to src/
#   make clean
#
# JWASM, JWLINK: the programs; GDI: the directory of INSTALL.EXE (and
# gdicheck) of https://github.com/geosone/gdi.

JWASM   ?= jwasm
JWLINK  ?= jwlink
GDI     ?= ../gdi/build
PYTHON  ?= python3
WATCOM  ?= /opt/watcom
WCL     ?= $(WATCOM)/binl64/wcl
CC      ?= cc

B       := build
REL     := $(B)/release
NAME    := vc49910a
SOURCES := $(wildcard src/*.ASM src/*.INC)
FILES   := $(shell cd files && find . -type f | sed 's|^\./||' | sort)
HELPS   := $(wildcard help/*.HLP)

# the published sources (the converter's input) and the LOOP/JCXZ lines
# TASM's JUMPS had to extend there (tools/tasm2jwasm.py -x)
SRCURL  := https://vc.vvv.kyiv.ua/download/src/vc49909.zip
SRCSHA  := b70fda9f9c94a321681dc49828f99ff4abe2c2f741e85c5bffab7ab6310b9f93
FAR     := VCARC2.INC:1188 VCDIALOG.INC:1921 VCMEM.INC:536 VCMENU.INC:631 \
           VCPANELS.INC:1601 VCPANELS.INC:1865 VCPANELS.INC:2123 VCVIEW.INC:1728

.PHONY: all release disk check test addons port clean

all: $(B)/VC.COM $(B)/VC.OVL addons

addons: $(B)/VCTOOLS.EXE

$(B)/VCTOOLS.EXE: addons/vctools.c | $(B)
	WATCOM="$(WATCOM)" INCLUDE="$(WATCOM)/h" PATH="$(WATCOM)/binl64:$$PATH" $(WCL) -q -bt=dos -0 -ms -os -w4 -we -fe=$@ -fo=$(B)/vctools.obj $<

$(B)/vctools-host: addons/vctools.c | $(B)
	$(CC) -std=c89 -Wall -Wextra -Werror -O2 -o $@ $<

$(B)/ADDONS.TXT: addons/README.de.md | $(B)
	$(PYTHON) -c 'from pathlib import Path; p=Path("$<"); s=p.read_text().replace("„", "\"").replace("“", "\"").replace("…", "..."); Path("$@").write_bytes(s.replace("\n", "\r\n").encode("cp850"))'

test: $(B)/vctools-host
	VCTOOLS=$(CURDIR)/$(B)/vctools-host $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

$(B):
	mkdir -p $@

$(B)/%.obj: src/%.ASM $(SOURCES) | $(B)
	cd src && $(JWASM) -q -c -DOFFICIAL -Fo=../$@ $(notdir $<)

# VC.COM: the resident part (tiny model), VC.OVL: the program (an EXE)
$(B)/VC.COM: $(B)/VC.obj
	$(JWLINK) format dos com file $< name $@ option quiet </dev/null

$(B)/VC.OVL: $(B)/VCOVL.obj
	$(JWLINK) format dos file $< name $@ option quiet </dev/null

release: $(B)/$(NAME).zip

$(B)/$(NAME).zip: all $(B)/ADDONS.TXT install/INSTALL.INI src/LICENSE.TXT $(addprefix files/,$(FILES)) $(HELPS)
	rm -rf $(REL) $@
	mkdir -p $(REL)
	cp -r files/. $(REL)/
	cp $(HELPS) $(REL)/
	cp $(B)/VC.COM $(B)/VC.OVL src/LICENSE.TXT install/INSTALL.INI $(GDI)/INSTALL.EXE $(REL)/
	cp $(B)/VCTOOLS.EXE $(REL)/
	cp $(B)/ADDONS.TXT $(REL)/
	cd $(REL) && zip -q -X -r ../$(NAME).zip .

check: release
	cd $(REL) && ../../$(GDI)/gdicheck INSTALL.INI

disk: $(B)/$(NAME).img

$(B)/$(NAME).img: $(B)/$(NAME).zip
	rm -f $@
	mformat -C -f 1440 -v VC49910A -i $@ ::
	cd $(REL) && mcopy -s -i ../$(NAME).img * ::

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
