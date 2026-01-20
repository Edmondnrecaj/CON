# Ensure that there are no spaces in path to avoid any undesired behavior
ifneq ($(word 2,$(realpath $(lastword $(MAKEFILE_LIST)))),)
$(error "ERROR: folder path contains spaces")
endif

MAKEFILEDIR ?= $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
SYNTHDIRNAME ?= _synth/
SYNTHDIR ?= $(MAKEFILEDIR)$(SYNTHDIRNAME)

BASE	 = lfsr
OBJ_NAME = lfsr.o
IVERILOG = iverilog
LIBRELANE = librelane
IVERILOG_FLAGS = -g2012

YOSYS = yosys

MATR_NUM := 0

#help	help		displays this help
.PHONY: help
help:
	@cat ${MAKEFILE_LIST} | sed -n 's/^#help//p'

#help	all		generates the verilog simulator
.PHONY: all
all: $(BASE).o
	vvp ./$(BASE).o

#help	clean		clean up temporary files
.PHONY: clean
clean:
	rm $(OBJ_NAME)
	rm -rf runs
	rm -rf $(SYNTHDIR)

#help	reference	print reference result based on entered immmatriculation number
.PHONY: reference
reference:
	@python3 ./reference.py $(MATR_NUM)

#help	build		builds the example module
.PHONY: build
build: $(BASE).o

$(BASE).o: lfsr.sv testbench.sv 
	$(IVERILOG) $(IVERILOG_FLAGS) -o $@ $^

#help	test		runs the example in the testbench
.PHONY: test
test: all

#help	view		runs the example in gtkwave
.PHONY: view
view: all
	$(GTKWAVE) $(BASE).vcd

#help 	synth		synthesizes the design with yosys
.PHONY: synth
synth:
	@mkdir -p $(SYNTHDIR)
	$(YOSYS) -T synth.ys

#help	gds		implements the design using LibreLane (must be running in Nix-shell)
.PHONY: gds
gds:
	$(LIBRELANE) implementation.json

#help	view-layout	opens final GDSII file in klayout
.PHONY: view-layout
view-layout: gds
	klayout runs/*/final/gds/*.gds

#help	build-synth	builds synthesized example module
.PHONY: build-synth
build-synth: $(SYNTHDIR)lfsr_synthesized.v lib/cmos_cells.v testbench.sv
	$(IVERILOG) $(IVERILOG_FLAGS) -o $(SYNTHDIR)lfsr_synthesized.o $^

#help	test-synth	runs the synthesized example in the testbench
.PHONY: test-synth
test-synth: build-synth
	vvp $(SYNTHDIR)lfsr_synthesized.o

#help	view-netlist	opens the netlist with yosys
.PHONY: view-netlist
view-netlist:
	xdot $(SYNTHDIR)lfsr_synth.dot
