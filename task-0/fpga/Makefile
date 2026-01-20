PROJ := lfsr_fpga
CONSTRAINTS := icebreaker.pcf
DEVICE := up5k
PACKAGE := sg48

ADD_SRC := ../lfsr.sv

# preserve artifacts
.SECONDARY: $(PROJ).v $(PROJ).json $(PROJ).asc

# SystemVerilog -> Verilog
%.v: %.sv
	sv2v $< $(ADD_SRC) > $@

# synthesis
%.json: %.v
	yosys -ql $*.log -p 'synth_ice40 -top $(PROJ) -json $@' $<

# implementation (place and route)
%.asc: $(CONSTRAINTS) %.json
	nextpnr-ice40 --$(DEVICE) \
	$(if $(PACKAGE),--package $(PACKAGE)) \
	--json $(filter-out $<,$^) \
	--pcf $< \
	--asc $@

# bitstream
%.bin: %.asc
	icepack $< $@

# flash final bitstream
.PHONY: flash
flash: $(PROJ).bin
	iceprog $<

.PHONY: clean
clean:
	rm -rf \
	$(PROJ).v \
	$(PROJ).json \
	$(PROJ).asc \
	$(PROJ).log \
	$(PROJ).bin
