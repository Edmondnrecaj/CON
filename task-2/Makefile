# Ensure that there are no spaces in path to avoid any undesired behavior
ifneq ($(word 2,$(realpath $(lastword $(MAKEFILE_LIST)))),)
$(error "ERROR: folder path contains spaces")
endif

MAKEFILEDIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
MAKEFILEDIRNAME := $(basename $(MAKEFILEDIR))

GCD_SV_SOURCES := src/gcd.sv tb/testbench.sv
LINTSOURCES ?= $(wildcard $(MAKEFILEDIR)/src/*.sv)
SIMDIR := $(MAKEFILEDIR)_sim/
SYNTHDIR := $(MAKEFILEDIR)_synth/
LIBRELANEDIR := $(MAKEFILEDIR)/runs/

GCD_SV := gcd

IVERILOGFLAGS ?= -Wall -g2012 -Wno-sensitivity-entire-array -I$(MAKEFILEDIR)

GTKWAVESAVE   ?= $(MAKEFILEDIR)$(GCD_SV).gtkw

ifeq (, $(shell which iverilog))
  IVERILOG      := iverilog-11 -g2012
else
  IVERILOG      := iverilog -g2012
endif

GTKWAVE  ?= gtkwave
YOSYS    ?= yosys
VERILATOR ?= verilator
LIBRELANE ?= librelane

#help	help		displays this help
.PHONY: help
help:
	@cat ${MAKEFILE_LIST} | sed -n 's/^#help//p'

#help	all		generates the verilog simulator
.PHONY: all
all: build

#help	clean		clean up temporary files
.PHONY: clean
clean:
	rm -rf $(SIMDIR)
	rm -rf $(SYNTHDIR)
	rm -rf $(LIBRELANEDIR)

#help	lint		uses verilator to show you syntax/design flaws
.PHONY: lint
lint:
	$(VERILATOR) --lint-only $(LINTSOURCES)

$(SIMDIR)gcd.vvp: $(GCD_SV_SOURCES)
	@mkdir -p $(SIMDIR)
	$(IVERILOG) $(IVERILOGFLAGS) -o $@ $(GCD_SV_SOURCES)

#help	build		builds the gcd module
.PHONY: build
build: $(SIMDIR)gcd.vvp ;

#help	test		runs the gcd in the testbench
.PHONY: test
test: $(SIMDIR)gcd.vvp
	vvp $(SIMDIR)gcd.vvp

#help	view		runs the gcd in gtkwave
.PHONY: view
view: $(SIMDIR)gcd.vvp
	$(SIMDIR)gcd.vvp
	$(GTKWAVE) --save $(GCD_SV).gtkw $(SIMDIR)gcd.vcd

#help 	synth		synthesizes the design with yosys
.PHONY: synth
synth:
	@mkdir -p $(SYNTHDIR)
	sv2v -E logic src/$(GCD_SV).sv -w $(SYNTHDIR)/gcd.v
	$(YOSYS) -T synth.ys

#help	gds		implements the design using LibreLane (must be running in Nix-shell)
.PHONY: gds
gds:
	$(LIBRELANE) implementation.json

#help	view-layout	opens final GDSII file in klayout
.PHONY: view-layout
view-layout:
	klayout runs/*/final/gds/*.gds

#help	build-synth	builds synthesized example module
.PHONY: build-synth
build-synth: $(SYNTHDIR)gcd_synthesized.v lib/cmos_cells.v tb/testbench.sv
	$(IVERILOG) $(IVERILOGFLAGS) -o $(SYNTHDIR)gcd_synthesized.vvp $^

#help	test-synth	runs the synthesized example in the testbench
.PHONY: test-synth
test-synth: build-synth
	vvp $(SYNTHDIR)gcd_synthesized.vvp
