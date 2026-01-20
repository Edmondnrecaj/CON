module sqrt (
    input  logic clk_i,
    input  logic rst_i,
    input  logic start_i,
    input  logic [31:0] a_i,

    output logic valid_o,
    output logic busy_o,
    output logic [31:0] result_o
);
    typedef enum logic [1:0] {INIT, COMP_D, SQRT} state_t;

    state_t state, next_state;
    logic [31:0] x_reg, r_reg, d_reg, a_reg;
    logic valid_reg;

    // Outputs
    assign busy_o    = (state != INIT);
    assign valid_o   = valid_reg;
    assign result_o  = r_reg;

    // State register + valid control
    always_ff @(posedge clk_i or posedge rst_i) begin
        if (rst_i) begin
            state     <= INIT;
            valid_reg <= 1'b0;
        end else begin
            state <= next_state;

            // Set valid when finishing
            if (state == SQRT && d_reg == 0 && next_state == INIT)
                valid_reg <= 1'b1;
            // Clear valid on new start
            else if (state == INIT && start_i)
                valid_reg <= 1'b0;
        end
    end

    // Next state logic
    always_comb begin
        next_state = state;
        case (state)
            INIT:    if (start_i)               next_state = COMP_D;
            COMP_D:  if (d_reg <= x_reg)        next_state = SQRT;
            SQRT:    if (d_reg == 0)            next_state = INIT;
            default:                            next_state = INIT;
        endcase
    end

    // Computation registers
    always_ff @(posedge clk_i or posedge rst_i) begin
        if (rst_i) begin
            x_reg <= 0;
            r_reg <= 0;
            d_reg <= 0;
            a_reg <= 0;
        end else begin
            case (state)
                INIT: begin
                    if (start_i) begin
                        a_reg <= a_i;
                        x_reg <= a_i;
                        r_reg <= 0;
                        d_reg <= 32'd1 << 30;
                    end
                end
                COMP_D: begin
                    if (d_reg > x_reg)
                        d_reg <= d_reg >> 2;
                end
                SQRT: begin
                    if (d_reg != 0) begin
                        if (x_reg >= r_reg + d_reg) begin
                            x_reg <= x_reg - (r_reg + d_reg);
                            r_reg <= (r_reg >> 1) + d_reg;
                        end else begin
                            r_reg <= r_reg >> 1;
                        end
                        d_reg <= d_reg >> 2;
                    end
                end
            endcase
        end
    end

endmodule