`define TIMEOUT 10000
`define HALF_CYCLE 50
`define FULL_CYCLE 100

module testbench_gcd ();
  logic         clk;
  logic         reset;
  logic         start;
  logic [31:0]  a;
  logic [31:0]  b;
  logic         busy;
  logic         valid;
  logic [31:0]  result;

  integer infile, outfile, read;
  logic [31:0] expected_gcd;

  gcd gcd_i(
    .clk_i      (clk),
    .rst_i      (reset),
    .start_i    (start),
    .a_i        (a),
    .b_i        (b),
    .busy_o     (busy),
    .valid_o    (valid),
    .result_o   (result)
  );

  always begin
    #`HALF_CYCLE clk = ~clk;
  end

  initial begin
    $dumpfile("_sim/gcd.vcd");
    $dumpvars(0, testbench_gcd);
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

  initial begin
    infile = $fopen("./testcases/testcases_gcd.txt", "r");
    outfile = $fopen("_sim/output_gcd.txt", "w");

    clk   = 0;
    start = 0;
    reset = 1;
    #`FULL_CYCLE
    reset = 0;
    #`FULL_CYCLE
    a = 0;
    b = 0;

    while (1 == 1) begin
      read = $fscanf(infile, "%d %d %d", a, b, expected_gcd);
      if (read == -1) begin
        $fdisplay(outfile, "All tests completed successfully!");
        $display("All tests completed successfully!");
        #`FULL_CYCLE
        #`FULL_CYCLE
        $finish();
      end

      wait(!busy);
      wait(!clk);

      #`FULL_CYCLE
      start = 1;
      #`FULL_CYCLE
      start = 0;
      wait(valid);
      #10
      $display("gcd(%d, %d) = %d (expected %d)", a, b, result, expected_gcd);
      $fdisplay(outfile, "gcd(%d, %d) = %d (expected %d)", a, b, result, expected_gcd);

      if (expected_gcd != result) begin
        $fdisplay(outfile, "Unexpected result on last computation!");
        $display("Unexpected result on last computation!");
        #200
        $finish();
      end
    end
  end
endmodule
