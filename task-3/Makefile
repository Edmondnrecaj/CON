# Ensure that there are no spaces in path to avoid any undesired behavior
ifneq ($(word 2,$(realpath $(lastword $(MAKEFILE_LIST)))),)
$(error "ERROR: folder path contains spaces")
endif

MAKEFILEDIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
MAKEFILEDIRNAME := $(basename $(MAKEFILEDIR))
ASMLIB := $(MAKEFILEDIR)/asmlib

DIVIDER_SV_SOURCES := ./ips/divider.sv testbed/testbed_divider.sv
SIMDIR := $(MAKEFILEDIR)_sim/
SYNTHDIR := $(MAKEFILEDIR)_synth/
LIBRELANEDIR := $(MAKEFILEDIR)/runs/
ASMDIR := $(MAKEFILEDIR)/testcases/
ASMSOURCES := $(wildcard $(ASMDIR)*.asm)
RTLSOURCES := $(MAKEFILEDIR)/ips/cpu_package.sv $(wildcard $(MAKEFILEDIR)/testbed/*.sv) $(wildcard $(MAKEFILEDIR)/ips/*.sv)
CPUNAME := riscv_core
CPUROOT :=
TEST_DIFFS = $(ASMSOURCES:$(ASMDIR)%.asm=$(SIMDIR)%.isa.diff) $(ASMSOURCES:$(ASMDIR)%.asm=$(SIMDIR)%.rtl.diff)
SYNTHSRC := ips/cpu_package.sv ips/alu.sv ips/divider.sv ips/register_file.sv ips/micro_riscv.sv

IVERILOGFLAGS ?= -Wall -g2012 -Wno-sensitivity-entire-array -I$(MAKEFILEDIR)/ips
RISCVASMFLAGS ?= -e $(MAKEFILEDIR)/div_extension.py
RISCVSIMFLAGS ?= --trace -e $(MAKEFILEDIR)/div_extension.py
GTKWAVESAVE   ?= $(MAKEFILEDIR)$(CPUNAME).gtkw

ifeq (, $(shell which iverilog))
  IVERILOG      := iverilog-11 -g2012
else
  IVERILOG      := iverilog -g2012
endif

GTKWAVE   ?= gtkwave
RISCVASM  ?= PYTHONPATH=$(ASMLIB) $(ASMLIB)/bin/riscvasm.py
RISCVSIM  ?= PYTHONPATH=$(ASMLIB) $(ASMLIB)/bin/riscvsim.py
YOSYS     ?= yosys
LIBRELANE ?= librelane
VERILATOR ?= verilator

#help
#help The main targets of this Makefile are:
#help	all	generates the verilog simulator and assembles the test programs
all: $(SIMDIR)$(CPUNAME).vvp $(ASMSOURCES:$(ASMDIR)%.asm=$(SIMDIR)%.hex) $(ASMSOURCES:$(ASMDIR)%.asm=$(SIMDIR)%.words.hex)

#help	clean	clean up temporary files
.PHONY: clean
clean:
	rm -rf $(SIMDIR)
	rm -rf $(SYNTHDIR)
	rm -rf $(LIBRELANEDIR)
	rm -rf __pycache__

#help	help	displays this help
.PHONY: help
help:
	@cat ${MAKEFILE_LIST} | sed -n 's/^#help//p'

$(SIMDIR)%.isa.diff: $(ASMDIR)%.ref.stdout $(SIMDIR)%.isa.stdout
	diff $^ | tee $@

$(SIMDIR)%.rtl.diff: $(ASMDIR)%.ref.stdout $(SIMDIR)%.rtl.stdout
	diff $^ | tee $@

#help	test	executes all simulations and checks stdout
.PHONY: test
test: $(TEST_DIFFS)
	@\
	n=0; p=0; f=0; \
	for t in $(TEST_DIFFS); do \
		n=$$((n + 1)); \
		echo -n ">> `basename $${t%.diff}`"; \
		if [ ! -s $$t ]; then \
			p=$$((p + 1)); \
			echo " [PASS]"; \
		else \
			f=$$((f + 1)); \
			echo " [FAIL]"; \
		fi; \
	done; \
	echo "Total:  $$n"; \
	echo "Passed: $$p"; \
	echo "Failed: $$f"; \
	exit $$f

###############################################################################
# COMPILATION
###############################################################################
.PRECIOUS: $(SIMDIR)%.hex
$(SIMDIR)%.hex: $(ASMDIR)%.asm
	@mkdir -p $(SIMDIR)
	$(RISCVASM) $(RISCVASMFLAGS) -o $@ $^

.PRECIOUS: $(SIMDIR)%.words.hex
$(SIMDIR)%.words.hex: $(ASMDIR)%.asm
	@mkdir -p $(SIMDIR)
	$(RISCVASM) $(RISCVASMFLAGS) -f words -o $@ $^

###############################################################################
# ISA SIMULATION
###############################################################################
SIM_LOG_ARGS = > $(SIMDIR)$*.isa.log
.PRECIOUS: $(SIMDIR)%.isa.stdout $(SIMDIR)%.isa.log
$(SIMDIR)%.isa.stdout $(SIMDIR)%.isa.log: $(SIMDIR)%.words.hex $(wildcard $(ASMDIR)*.stdin)
	cp $(ASMDIR)$*.stdin $(SIMDIR)stdin.txt || touch $(SIMDIR)stdin.txt
	$(RISCVSIM) $< $(RISCVSIMFLAGS) --stdin $(SIMDIR)stdin.txt --stdout $(SIMDIR)$*.isa.stdout $(SIM_LOG_ARGS)

###############################################################################
# RTL SIMULATION
###############################################################################
ifeq (${CPUROOT},)
$(SIMDIR)$(CPUNAME).vvp: $(RTLSOURCES)
	@mkdir -p $(SIMDIR)
	$(IVERILOG) $(IVERILOGFLAGS) -o $@ -s testbed $^
else
$(SIMDIR)$(CPUNAME).vvp:
	cd $(CPUROOT) && $(MAKE) $(SIMDIR)$(CPUNAME).vvp
	@mkdir -p $(SIMDIR)
	cp $(CPUROOT)$(SIMDIR)$(CPUNAME).vvp $(SIMDIR)
endif

LOG_ARGS = > $*.rtl.log
.PRECIOUS: $(SIMDIR)%.vcd $(SIMDIR)%.rtl.stdout $(SIMDIR)%.rtl.log
$(SIMDIR)%.vcd $(SIMDIR)%.rtl.stdout $(SIMDIR)%.rtl.log: $(SIMDIR)%.hex $(SIMDIR)$(CPUNAME).vvp $(wildcard $(ASMDIR)*.stdin)
	cp $(ASMDIR)$*.stdin $(SIMDIR)stdin.txt || touch $(SIMDIR)stdin.txt
	cd $(SIMDIR) && vvp ./$(CPUNAME).vvp +PROGRAM=$*.hex $(LOG_ARGS)
	mv $(SIMDIR)$(CPUNAME).vcd $(SIMDIR)$*.vcd
	mv $(SIMDIR)stdout.txt $(SIMDIR)$*.rtl.stdout

$(SIMDIR)divider.vvp: $(DIVIDER_SV_SOURCES)
	@mkdir -p $(SIMDIR)
	$(IVERILOG) $(IVERILOGFLAGS) -o $@ $(DIVIDER_SV_SOURCES)

#help
#help	divider                         builds the divider module alone
divider: $(SIMDIR)divider.vvp ;

#help	run_divider                     runs the divider in the isolated testbed
#help
run_divider: $(SIMDIR)divider.vvp
	vvp $(SIMDIR)divider.vvp

#help	view_divider                     runs the divider in the isolated testbed
#help
view_divider: $(SIMDIR)divider.vvp
	vvp $(SIMDIR)divider.vvp
	$(GTKWAVE) --save $(CPUROOT)divider.gtkw $(SIMDIR)divider.vcd

###############################################################################
# INTERACTIVE TARGETS
###############################################################################
#help
#help	sim TARGET=<target_name>	runs the ISA simulation of the target
.PHONY: sim run view
sim:
ifeq (${TARGET},)
	@echo "ERROR: No TARGET has been specified!"
	@echo "Usage: make $@ TARGET=<target_name>"
	@exit 1
endif # TARGET is empty
	rm -f $(SIMDIR)${TARGET}.isa.log
	@$(MAKE) --no-print-directory $(SIMDIR)${TARGET}.isa.log TARGET=$(TARGET) SIM_LOG_ARGS="| tee \$$(SIMDIR)\$$*.isa.log"

#help	run TARGET=<target_name>	runs the verilog simulation of the target
run:
ifeq (${TARGET},)
	@echo "ERROR: No TARGET has been specified!"
	@echo "Usage: make $@ TARGET=<target_name>"
	@exit 1
endif # TARGET is empty
	rm -f $(SIMDIR)${TARGET}.rtl.log
	@$(MAKE) --no-print-directory $(SIMDIR)${TARGET}.rtl.log TARGET=$(TARGET) LOG_ARGS="| tee \$$*.rtl.log"

#help	view TARGET=<target_name>	views the waveforms from the verilog simulation of the target
view:
ifeq (${TARGET},)
	@echo "ERROR: No TARGET has been specified!"
	@echo "Usage: make $@ TARGET=<target_name>"
	@exit 1
endif # TARGET is empty
	@$(MAKE) --no-print-directory $(SIMDIR)${TARGET}.vcd TARGET=$(TARGET)
	$(GTKWAVE) --save $(CPUROOT)$(CPUNAME).gtkw $(SIMDIR)$(TARGET).vcd

#help 	synth    			synthesizes the design with yosys
synth:
	@mkdir -p $(SYNTHDIR)
	sv2v $(SYNTHSRC) -w $(SYNTHDIR)/micro_riscv.v
	$(YOSYS) -T synth.ys

#help	gds				implements the design using LibreLane (must be running in Nix-shell)
.PHONY: gds view-layout
gds:
	sv2v $(SYNTHSRC) -w $(SYNTHDIR)/micro_riscv.v
	$(LIBRELANE) implementation.json

#help	view-layout			opens final GDSII file in klayout
view-layout:
	klayout runs/*/final/gds/*.gds

#help	lint	uses verilator to show you syntax/design flaws
lint:
	$(VERILATOR) --lint-only -I$(MAKEFILEDIR)/ips $(LINTSOURCES)
