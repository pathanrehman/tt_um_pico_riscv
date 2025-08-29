`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb ();

  // Dump the signals to a VCD file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb.vcd");
    $dumpvars(0, tb);
    #1;
  end

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

  // Replace tt_um_example with your module name:
  tt_um_pico_riscv user_project (
      // Include power ports for the Gate Level test:
`ifdef GL_TEST
      .VPWR(VPWR),
      .VGND(VGND),
`endif
      .ui_in  (ui_in),    // Dedicated inputs
      .uo_out (uo_out),   // Dedicated outputs
      .uio_in (uio_in),   // IOs: Input path
      .uio_out(uio_out),  // IOs: Output path
      .uio_oe (uio_oe),   // IOs: Enable path (active high: 0=input, 1=output)
      .ena    (ena),      // enable - goes high when design is selected
      .clk    (clk),      // clock
      .rst_n  (rst_n)     // not reset
  );

  // Debug signals only available in RTL simulation
`ifndef GL_TEST
  // Additional debug signals for PicoRISC-V educational visibility
  wire [15:0] current_instruction = user_project.instruction_reg;
  wire [7:0] register_0 = user_project.registers[0];
  wire [7:0] register_1 = user_project.registers[1];
  wire [7:0] register_2 = user_project.registers[2];
  wire [7:0] register_3 = user_project.registers[3];
  wire [7:0] register_4 = user_project.registers[4];
  wire [7:0] register_5 = user_project.registers[5];
  wire [7:0] register_6 = user_project.registers[6];
  wire [7:0] register_7 = user_project.registers[7];
  wire [7:0] program_counter = user_project.pc;
  wire instruction_valid = user_project.instruction_valid;
  wire branch_taken = user_project.branch_taken;
  wire [7:0] alu_result = user_project.alu_result;
  wire load_state = user_project.load_state;
  wire [2:0] current_rd = user_project.current_rd;
`endif
  
endmodule
