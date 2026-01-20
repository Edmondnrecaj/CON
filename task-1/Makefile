# Ensure that there are no spaces in path to avoid any undesired behavior
ifneq ($(word 2,$(realpath $(lastword $(MAKEFILE_LIST)))),)
$(error "ERROR: folder path contains spaces")
endif

MAKEFILEDIR ?= $(dir $(realpath $(lastword $(MAKEFILE_LIST))))

RTLSOURCES ?= $(wildcard $(MAKEFILEDIR)/tb/*.sv) $(wildcard $(MAKEFILEDIR)/src/*.sv)
LINTSOURCES ?= $(wildcard $(MAKEFILEDIR)/src/*.sv)
RTLNAME ?= sqrt
TESTDIR ?= $(abspath ../task-1/test)/
TESTS ?= $(wildcard $(TESTDIR)*.testvec)

SIMDIRNAME ?= _sim/
SYNTHDIRNAME ?= _synth/
SIMDIR ?= $(MAKEFILEDIR)$(SIMDIRNAME)
SYNTHDIR ?= $(MAKEFILEDIR)$(SYNTHDIRNAME)
LIBRELANEDIR := $(MAKEFILEDIR)/runs/
TARGET ?= square

IVERILOGFLAGS ?= -Wall -g2012 -Wno-sensitivity-entire-array
IVERILOG ?= iverilog
VERILATOR ?= verilator
GTKWAVE  ?= gtkwave
YOSYS ?= yosys
LIBRELANE ?= librelane

#help	help		displays this help
.PHONY: help
help:
	@cat ${MAKEFILE_LIST} | sed -n 's/^#help//p'

#help	all		generates the verilog simulator
.PHONY: all
all: $(SIMDIR)$(RTLNAME).vvp

#help	clean		clean up temporary files
.PHONY: clean
clean:
	rm -rf $(SIMDIR)
	rm -rf $(SYNTHDIR)
	rm -rf $(LIBRELANEDIR)

#help	lint		uses verilator to show you syntax/design flaws
lint:
	$(VERILATOR) --lint-only $(LINTSOURCES)

#help	build		builds the example module
.PHONY: build
build: $(SIMDIR)$(RTLNAME).vvp

#help	test		runs the example in the testbench
.PHONY: test
test: $(SIMDIR)$(RTLNAME).vvp
	cp $(TESTDIR)/$(TARGET).testvec  $(SIMDIR)/input.txt
	cd $(SIMDIR) && vvp $(SIMDIR)$(RTLNAME).vvp


$(SIMDIR)$(RTLNAME).vvp: $(RTLSOURCES)
	@mkdir -p $(SIMDIR)
	$(IVERILOG) $(IVERILOGFLAGS) -o $@ $(RTLSOURCES) 
LOG_ARGS = > $*.rtl.log
$(SIMDIR)%.rtl.log: $(TESTDIR)%.testvec $(SIMDIR)$(RTLNAME).vvp
	cp $< $(SIMDIR)input.txt
	cd $(SIMDIR) && vvp ./$(RTLNAME).vvp > $@

$(SIMDIR)%.out: $(SIMDIR)%.rtl.log
	cp $(SIMDIR)output.txt $@

$(SIMDIR)%.vcd: $(SIMDIR)%.rtl.log
	cp $(SIMDIR)$(RTLNAME).vcd $@

#help	view		views the waveforms from the verilog simulation of the target
.PHONY: view
view:
	@$(MAKE) -f $(MAKEFILEDIR)Makefile --no-print-directory $(SIMDIR)$(RTLNAME).vcd
	$(GTKWAVE) --save $(MAKEFILEDIR)$(RTLNAME).gtkw $(SIMDIR)$(RTLNAME).vcd

#help 	synth    	synthesizes the design with yosys
.PHONY: synth
synth:
	@mkdir -p $(SYNTHDIR)
	sv2v --incdir src -E logic src/*.sv -w $(SYNTHDIR)/$(RTLNAME).v
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
build-synth: $(SYNTHDIR)sqrt_synthesized.v lib/cmos_cells.v tb/testbench.sv
	$(IVERILOG) $(IVERILOGFLAGS) -o $(SYNTHDIR)sqrt_synthesized.vvp $^

#help	test-synth	runs the synthesized example in the testbench
.PHONY: test-synth
test-synth: build-synth
	cp $(TESTDIR)/$(TARGET).testvec  $(SYNTHDIR)/input.txt
	cd $(SYNTHDIR) && vvp sqrt_synthesized.vvp

SYNTH_LOG_ARGS = > $*.syn.rtl.log
$(SIMDIR)%.syn.rtl.log: $(TESTDIR)%.testvec build-synth
	cp $< $(SIMDIR)input.txt
	cd $(SIMDIR) && vvp ./$(SYNTHDIR)sqrt_synthesized.vvp > $@

$(SIMDIR)%.syn.out: $(SIMDIR)%.syn.rtl.log
	cp $(SIMDIR)output.txt $@


