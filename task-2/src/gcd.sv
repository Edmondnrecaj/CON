module gcd (
    input  logic        clk_i,
    input  logic        rst_i,
    input  logic        start_i,
    input  logic [31:0] a_i,
    input  logic [31:0] b_i,
    output logic        busy_o,
    output logic        valid_o,
    output logic [31:0] result_o
);

    // -----------------------------------------------------------------
    //  registers that hold the current values
    // -----------------------------------------------------------------
    logic [31:0] a, a_nxt;
    logic [31:0] b, b_nxt;
    logic [5:0]  k, k_nxt;          // power-of-2 factor
    logic [31:0] result, result_nxt;

    // -----------------------------------------------------------------
    //  state machine encoding
    // -----------------------------------------------------------------
    typedef enum logic [3:0] {
        IDLE       = 4'b0000,
        LOAD       = 4'b0001,
        CHK_ZERO   = 4'b0010,
        FACTOR2    = 4'b0011,
        STRIP_A    = 4'b0100,
        STRIP_B    = 4'b0101,
        CMP        = 4'b0110,
        SUB        = 4'b0111,
        DONE       = 4'b1000
    } state_t;

    state_t state, state_nxt;

    // -----------------------------------------------------------------
    //  handy condition wires
    // -----------------------------------------------------------------
    logic a_is_zero, b_is_zero;
    logic both_even, a_even, b_even;
    logic a_gt_b;
    logic b_will_be_zero;          // look-ahead for the subtract state

    assign a_is_zero = (a == 0);
    assign b_is_zero = (b == 0);
    assign both_even = (a[0] == 0) && (b[0] == 0);
    assign a_even    = (a[0] == 0);
    assign b_even    = (b[0] == 0);
    assign a_gt_b    = (a > b);

    // -----------------------------------------------------------------
    //  control flags (set only when needed)
    // -----------------------------------------------------------------
    logic load_inputs, inc_k, shift_a, shift_b, swap, set_res;

    // -----------------------------------------------------------------
    //  next-state + datapath combinational logic
    // -----------------------------------------------------------------
    always_comb begin
        // ---- default assignments (avoid latches) --------------------
        state_nxt   = state;
        load_inputs = 1'b0;
        inc_k       = 1'b0;
        shift_a     = 1'b0;
        shift_b     = 1'b0;
        swap        = 1'b0;
        set_res     = 1'b0;

        a_nxt      = a;
        b_nxt      = b;
        k_nxt      = k;
        result_nxt = result;

        b_will_be_zero = 1'b0;

        // -------------------------------------------------------------
        //  the big case – each state decides what to do next
        // -------------------------------------------------------------
        case (state)

            IDLE: begin
                if (start_i) begin
                    load_inputs = 1'b1;          // remember we are loading
                    state_nxt   = LOAD;
                end
            end

            LOAD: begin
                a_nxt = a_i;                     // grab the inputs
                b_nxt = b_i;
                k_nxt = 6'd0;                    // reset factor
                state_nxt = CHK_ZERO;
            end

            CHK_ZERO: begin
                if (a_is_zero && b_is_zero) begin
                    set_res     = 1'b1;
                    result_nxt  = 32'd0;
                    state_nxt   = DONE;
                end else if (a_is_zero) begin
                    set_res     = 1'b1;
                    result_nxt  = b;
                    state_nxt   = DONE;
                end else if (b_is_zero) begin
                    set_res     = 1'b1;
                    result_nxt  = a;
                    state_nxt   = DONE;
                end else begin
                    state_nxt = FACTOR2;
                end
            end

            FACTOR2: begin
                if (both_even) begin
                    shift_a = 1'b1;
                    shift_b = 1'b1;
                    inc_k   = 1'b1;

                    a_nxt = a >> 1;
                    b_nxt = b >> 1;
                    k_nxt = k + 1'b1;

                    state_nxt = FACTOR2;          // stay here while both even
                end else begin
                    state_nxt = STRIP_A;
                end
            end

            STRIP_A: begin
                if (a_even) begin
                    shift_a = 1'b1;
                    a_nxt   = a >> 1;
                    state_nxt = STRIP_A;
                end else begin
                    state_nxt = STRIP_B;
                end
            end

            STRIP_B: begin
                if (b_even) begin
                    shift_b = 1'b1;
                    b_nxt   = b >> 1;
                    state_nxt = STRIP_B;
                end else begin
                    state_nxt = CMP;
                end
            end

            CMP: begin
                if (a_gt_b) begin
                    swap  = 1'b1;
                    a_nxt = b;
                    b_nxt = a;
                end
                state_nxt = SUB;
            end

            SUB: begin
                b_nxt = b - a;                     // the only real arithmetic
                b_will_be_zero = (b_nxt == 0);

                if (b_will_be_zero) begin
                    set_res     = 1'b1;
                    result_nxt  = a << k;        // restore the 2^k factor
                    state_nxt   = DONE;
                end else begin
                    state_nxt = STRIP_B;
                end
            end

            DONE: begin
                state_nxt = IDLE;                 // back to waiting
            end

            default: state_nxt = IDLE;           // safety

        endcase
    end

    // -----------------------------------------------------------------
    //  datapath registers (with async reset)
    // -----------------------------------------------------------------
    always_ff @(posedge clk_i or posedge rst_i) begin
        if (rst_i) begin
            a      <= 32'd0;
            b      <= 32'd0;
            k      <= 6'd0;
            result <= 32'd0;
        end else begin
            a      <= a_nxt;
            b      <= b_nxt;
            k      <= k_nxt;
            result <= result_nxt;
        end
    end

    // -----------------------------------------------------------------
    //  state register (async reset)
    // -----------------------------------------------------------------
    always_ff @(posedge clk_i or posedge rst_i) begin
        if (rst_i)
            state <= IDLE;
        else
            state <= state_nxt;
    end

    // -----------------------------------------------------------------
    //  output logic – also registered so we have a clean interface
    // -----------------------------------------------------------------
    always_ff @(posedge clk_i or posedge rst_i) begin
        if (rst_i) begin
            busy_o   <= 1'b0;
            valid_o  <= 1'b0;
            result_o <= 32'd0;
        end else begin
            // busy while we are not idle and not done
            busy_o   <= (state != IDLE) && (state != DONE);
            valid_o  <= set_res;               // pulse for one cycle
            result_o <= result_nxt;
        end
    end

endmodule