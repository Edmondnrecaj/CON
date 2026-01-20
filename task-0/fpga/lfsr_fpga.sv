// ############################################################################
// Wrapper for the Task-0 LFSR to deploy it on an iCEBreaker FPGA board.
//
// Author: Moritz Waser

module lfsr_fpga (
    input logic clk_i,
    input logic rst_i,

    output logic pmod2_led1,
    output logic pmod2_led2,
    output logic pmod2_led3,
    output logic pmod2_led4,
    output logic pmod2_led5,

    input logic pmod2_btn1, // controls clock rotation
    input logic pmod2_btn2  // controls red LED
);

    // ########################################################################
    // Design
    logic [31:0] lfsr_state;
    logic pmod2_btn1_clean;

    lfsr my_lfsr (
        .clk_i        (pmod2_btn1_clean),
        .reset_i      (          ~rst_i),
        .lfsr_state_o (      lfsr_state)
        );

    debouncer pmod2_btn1_debounce (
        .clk_i (clk_i),
        .rst_i (~rst_i),
        .noisy_i (pmod2_btn1),
        .clean_o (pmod2_btn1_clean)
        );

    // Use shift register value as output for LEDs
    assign {pmod2_led2, pmod2_led5, pmod2_led3, pmod2_led4} = lfsr_state[3:0];

    //assign pmod2_led1 = pmod2_btn1_clean;
endmodule


// ############################################################################
// Simple debouncer circuit for button inputs
//
module debouncer #(
    parameter integer STABLE_CYCLES = 128  // how many cycles input must stay stable
) (
    input  logic clk_i,
    input  logic rst_i,
    input  logic noisy_i,   // raw button/switch input
    output logic clean_o   // debounced output
);

    logic noisy_sync, noisy_sync_d;   // synchronize input to clk domain
    logic [$clog2(STABLE_CYCLES):0] counter_p, counter_n;
    logic clean_p, clean_n;

    // 2-flop synchronizer for metastability
    always_ff @(posedge clk_i or posedge rst_i) begin
        if (rst_i) begin
            noisy_sync   <= 1'b0;
            noisy_sync_d <= 1'b0;
        end else begin
            noisy_sync   <= noisy_i;
            noisy_sync_d <= noisy_sync;
        end
    end


    
    always_comb begin
        counter_n = counter_p + 1;
        clean_n = clean_p;

        // no change
        if (noisy_sync_d == clean_p) begin
            counter_n = '0;
        end else if (counter_p == STABLE_CYCLES - 1) begin
            clean_n = noisy_sync_d;
            counter_n = '0;
        end
    end

    // debounce counter
    always_ff @(posedge clk_i or posedge rst_i) begin
        if (rst_i) begin
            counter_p <= '0;
            clean_p   <= 1'b0;
        end else begin
            counter_p <= counter_n;
            clean_p   <= clean_n;
        end
    end

    assign clean_o = clean_p;

endmodule
