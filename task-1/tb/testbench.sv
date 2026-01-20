`define QUARTER_PERIOD 1
`define HALF_PERIOD 2
`define PERIOD 4
`define RESET_DELAY (`HALF_PERIOD + 1)
`define TIMEOUT 10000

// BEGIN ORGANIZATION
`define ASSERT(signal, value) \
    if (signal !== value) begin \
        $display("ASSERTION FAILED in %m: signal != value"); \
        $finish; \
    end
// END ORGANIZATION

module sqrt_tb ();

    // reset generation
    logic reset = 0;
    typedef enum logic [1:0] {LOAD_N, CALC} state_t;

    // clock generation
    logic clk;
    initial clk = 0;
    always begin
        #`HALF_PERIOD clk = ~clk;
    end

    // tick counter
    integer ticks = 0;
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            ticks <= 0;
        end else begin
            ticks <= ticks + 1;
            if (ticks > `TIMEOUT) begin
                $write("Testbench ran into TIMEOUT!\n");
                $finish();
            end
        end
    end

    // dut signals
    logic [31:0] sqrt_inp_a;
    logic        sqrt_inp_start;

    logic [31:0] sqrt_result;
    logic        sqrt_output_valid;
    logic        sqrt_output_busy;

    // file descriptors
    integer inp_file, outp_file, ret;

    // reference value from testvec
    logic [31:0] sqrt_result_ref;

    // device under test (DUT)
    sqrt dut (
        .clk_i          ( clk               ),
        .rst_i          ( reset             ),
        .a_i            ( sqrt_inp_a        ),
        .start_i        ( sqrt_inp_start    ),
        .result_o       ( sqrt_result       ),
        .valid_o        ( sqrt_output_valid     ),
        .busy_o         ( sqrt_output_busy  )
        );

    // dump variables for gtkwave
    initial begin
        $dumpfile("sqrt.vcd");
        $dumpvars(0, sqrt_tb);
    end

    task static reset_dut(input logic rst);
        reset = 0;
        reset = 1;
        #`RESET_DELAY
        reset = 0;
    endtask

    // Read <VALUE> <RESULT> from input file and check whether the result of the module
    // matches the expected result.
    // Stop if EOF is detected.
    task static run_testcase(input integer tc_file, input integer out_file, output integer ret);
        // Check if there is still something to read. If not, abort
        ret = 0;
        if (!$feof(tc_file))
            begin
            ret = $fscanf(tc_file, "%d %d", sqrt_inp_a, sqrt_result_ref);
            if (ret == 2) begin
                $display("Test input %0d with expected result %0d", sqrt_inp_a, sqrt_result_ref);
                // Reset device under test to move to init state. Input a_i is applied at all times
                reset_dut(reset);
                // Wait for a Period, raise start signal, wait for another period and drop start signal.
                #`PERIOD
                sqrt_inp_start = 1'b1;
                #`PERIOD
                sqrt_inp_start = 1'b0;
                #`PERIOD
                // Wait until the module sets valid_o. IF THIS VALUE IS NEVER SET WE STALL HERE!
                wait(sqrt_output_valid);
                #`PERIOD
                $fdisplay(out_file, "%0d %b", sqrt_result, sqrt_output_valid);
                if (sqrt_result == sqrt_result_ref) begin
                    $display("Result matches expected value %0d\n", sqrt_result_ref);
                end
                else begin
                    $display("!! Result %0d does not match expected value %0d !!\n", sqrt_result,sqrt_result_ref);
                end
            end
        end
    endtask

    // BEGIN ORGANIZATION

    // checks whether clear signal resets input registers
    task static run_test_advanced();
        $display("Running advanced tests!");
        sqrt_inp_a = 64;
        reset_dut(reset);
        #`PERIOD
        sqrt_inp_start = 1'b1;
        #`PERIOD
        sqrt_inp_start = 1'b0;
        #`PERIOD
        // Wait until the module sets valid_o. IF THIS VALUE IS NEVER SET WE STALL HERE!
        wait(sqrt_output_valid);
        #`PERIOD
        $display("Output was %0d\n",sqrt_result);
        // First, check what happens if we raise start twice for a short amount of time. This should not trigger anything.
        $display("Check what happens if start is asserted for a less than a period!");
        #`QUARTER_PERIOD
        sqrt_inp_start = 1'b1;
        #`QUARTER_PERIOD
        sqrt_inp_start = 1'b0;
        `ASSERT(sqrt_output_busy,0);
        `ASSERT(sqrt_output_valid,1);

        //#`HALF_PERIOD
        sqrt_inp_start = 1'b1;
        #`QUARTER_PERIOD
        sqrt_inp_start = 1'b0;
        #`HALF_PERIOD
        sqrt_inp_start = 1'b1;
        #`QUARTER_PERIOD
        sqrt_inp_start = 1'b0;
        `ASSERT(sqrt_output_busy,0);
        `ASSERT(sqrt_output_valid,1);
        $display("Seems like start is only checked at rising edge, good.");
        // Start computation, change input and try to restart.
        sqrt_inp_a = 25;
        sqrt_inp_start = 1'b1;
        #`PERIOD
        sqrt_inp_start = 1'b0;
        #`PERIOD
        wait(sqrt_output_busy);
        sqrt_inp_a = 9;
        sqrt_inp_start = 1'b1;
        #`PERIOD
        sqrt_inp_start = 1'b0;
        #`PERIOD
        wait(sqrt_output_valid);
        `ASSERT(sqrt_output_valid,1);
        `ASSERT(sqrt_output_busy,0);
        `ASSERT(sqrt_result,5);
        $display("Result correct.");


    endtask

    // checks whether it's possible to reload input registers before
    // calculating something
    //task static run_load_test();
    //    reset_dut(reset);
    //    calc_inp_a = 5'b00001;
    //    calc_inp_b = 5'b00001;
    //    calc_inp_v = 1'b1;
    //    #`PERIOD
    //    #`PERIOD
    //    calc_inp_a = 5'b00100;
    //    calc_inp_b = 5'b00100;
    //    #`PERIOD
    //    #`PERIOD
    //    calc_inp_v = 1'b0;
    //    calc_calc = 1'b1;
    //    #`PERIOD
    //    calc_calc = 1'b0;
    //    `ASSERT(calc_result, 5'b01000);
    //endtask
//
    // checks whether input registers get updated even though the state
    // machine is in the CALC state (out of spec behavior)
    //task static run_reg_test();
    //    reset_dut(reset);
    //    calc_inp_a = 5'b00001;
    //    calc_inp_b = 5'b00001;
    //    calc_inp_v = 1'b1;
    //    #`PERIOD
    //    #`PERIOD
    //    calc_calc = 1'b1;
    //    #`PERIOD
    //    calc_calc = 1'b0;
    //    `ASSERT(calc_result, 5'b00010);
    //    calc_inp_a = 5'b00010;
    //    calc_inp_b = 5'b00010;
    //    #`PERIOD
    //    #`PERIOD
    //    `ASSERT(calc_result, 5'b00010);
    //endtask

    // checks whether result is directly connected to output and affected by
    // the mode_i signal
    //task static run_mode_test();
    //    reset_dut(reset);
    //    calc_inp_a = 5'b00000;
    //    calc_inp_b = 5'b00001;
    //    calc_inp_v = 1'b1;
    //    #`PERIOD
    //    #`PERIOD
    //    calc_calc = 1'b1;
    //    #`PERIOD
    //    calc_calc = 1'b0;
    //    `ASSERT(calc_result, 5'b00001);
    //    #`PERIOD
    //    calc_mode = 1'b1;
    //    `ASSERT(calc_result, 5'b11111);
    //    calc_mode = 1'b0;
    //endtask
    // END ORGANIZATION

    initial begin
        reset_dut(reset);

        // testvector handling
        ret = 1;
        inp_file = $fopen("input.txt", "r");
        outp_file = $fopen("output.txt", "w");
        sqrt_inp_start = 0;
        while (ret != 0) begin
            run_testcase(inp_file, outp_file, ret);
        end

        // BEGIN ORGANIZATION

        run_test_advanced();

        // END ORGANIZATION

        $finish();
    end
endmodule
