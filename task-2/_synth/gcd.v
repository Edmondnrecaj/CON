module gcd (
	clk_i,
	rst_i,
	start_i,
	a_i,
	b_i,
	busy_o,
	valid_o,
	result_o
);
	reg _sv2v_0;
	input logic clk_i;
	input logic rst_i;
	input logic start_i;
	input logic [31:0] a_i;
	input logic [31:0] b_i;
	output logic busy_o;
	output logic valid_o;
	output logic [31:0] result_o;
	logic [31:0] a;
	logic [31:0] a_nxt;
	logic [31:0] b;
	logic [31:0] b_nxt;
	logic [5:0] k;
	logic [5:0] k_nxt;
	logic [31:0] result;
	logic [31:0] result_nxt;
	logic [3:0] state;
	logic [3:0] state_nxt;
	logic a_is_zero;
	logic b_is_zero;
	logic both_even;
	logic a_even;
	logic b_even;
	logic a_gt_b;
	logic b_will_be_zero;
	assign a_is_zero = a == 0;
	assign b_is_zero = b == 0;
	assign both_even = (a[0] == 0) && (b[0] == 0);
	assign a_even = a[0] == 0;
	assign b_even = b[0] == 0;
	assign a_gt_b = a > b;
	logic load_inputs;
	logic inc_k;
	logic shift_a;
	logic shift_b;
	logic swap;
	logic set_res;
	always @(*) begin
		if (_sv2v_0)
			;
		state_nxt = state;
		load_inputs = 1'b0;
		inc_k = 1'b0;
		shift_a = 1'b0;
		shift_b = 1'b0;
		swap = 1'b0;
		set_res = 1'b0;
		a_nxt = a;
		b_nxt = b;
		k_nxt = k;
		result_nxt = result;
		b_will_be_zero = 1'b0;
		case (state)
			4'b0000:
				if (start_i) begin
					load_inputs = 1'b1;
					state_nxt = 4'b0001;
				end
			4'b0001: begin
				a_nxt = a_i;
				b_nxt = b_i;
				k_nxt = 6'd0;
				state_nxt = 4'b0010;
			end
			4'b0010:
				if (a_is_zero && b_is_zero) begin
					set_res = 1'b1;
					result_nxt = 32'd0;
					state_nxt = 4'b1000;
				end
				else if (a_is_zero) begin
					set_res = 1'b1;
					result_nxt = b;
					state_nxt = 4'b1000;
				end
				else if (b_is_zero) begin
					set_res = 1'b1;
					result_nxt = a;
					state_nxt = 4'b1000;
				end
				else
					state_nxt = 4'b0011;
			4'b0011:
				if (both_even) begin
					shift_a = 1'b1;
					shift_b = 1'b1;
					inc_k = 1'b1;
					a_nxt = a >> 1;
					b_nxt = b >> 1;
					k_nxt = k + 1'b1;
					state_nxt = 4'b0011;
				end
				else
					state_nxt = 4'b0100;
			4'b0100:
				if (a_even) begin
					shift_a = 1'b1;
					a_nxt = a >> 1;
					state_nxt = 4'b0100;
				end
				else
					state_nxt = 4'b0101;
			4'b0101:
				if (b_even) begin
					shift_b = 1'b1;
					b_nxt = b >> 1;
					state_nxt = 4'b0101;
				end
				else
					state_nxt = 4'b0110;
			4'b0110: begin
				if (a_gt_b) begin
					swap = 1'b1;
					a_nxt = b;
					b_nxt = a;
				end
				state_nxt = 4'b0111;
			end
			4'b0111: begin
				b_nxt = b - a;
				b_will_be_zero = b_nxt == 0;
				if (b_will_be_zero) begin
					set_res = 1'b1;
					result_nxt = a << k;
					state_nxt = 4'b1000;
				end
				else
					state_nxt = 4'b0101;
			end
			4'b1000: state_nxt = 4'b0000;
			default: state_nxt = 4'b0000;
		endcase
	end
	always @(posedge clk_i or posedge rst_i)
		if (rst_i) begin
			a <= 32'd0;
			b <= 32'd0;
			k <= 6'd0;
			result <= 32'd0;
		end
		else begin
			a <= a_nxt;
			b <= b_nxt;
			k <= k_nxt;
			result <= result_nxt;
		end
	always @(posedge clk_i or posedge rst_i)
		if (rst_i)
			state <= 4'b0000;
		else
			state <= state_nxt;
	always @(posedge clk_i or posedge rst_i)
		if (rst_i) begin
			busy_o <= 1'b0;
			valid_o <= 1'b0;
			result_o <= 32'd0;
		end
		else begin
			busy_o <= (state != 4'b0000) && (state != 4'b1000);
			valid_o <= set_res;
			result_o <= result_nxt;
		end
	initial _sv2v_0 = 0;
endmodule