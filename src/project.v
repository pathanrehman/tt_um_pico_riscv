`default_nettype none
module tt_um_simple_riscv (
input  wire [7:0] ui_in,    // Dedicated inputs
output wire [7:0] uo_out,   // Dedicated outputs
input  wire [7:0] uio_in,   // IOs: Input path
output wire [7:0] uio_out,  // IOs: Output path
output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
input  wire       ena,      // always 1 when the design is powered, so you can ignore it
input  wire       clk,      // clock
input  wire       rst_n     // reset_n - low to reset
);
// All output pins must be assigned. If not used, assign to 0.
assign uio_out = 0;
assign uio_oe  = 0;
// List all unused inputs to prevent warnings
wire _unused = &{ena, ui_in, uio_in, 1'b0};
reg [3:0] pc;  // 4-bit PC for 16 instructions
reg [7:0] regfile [0:15];  // 16 x 8-bit registers
wire [31:0] instr;
always @(*) begin
case (pc)
4'd0: instr = {7'b0000000, 5'b00011, 5'b00010, 3'b000, 5'b00001, 7'b0110011};  // add x1, x2, x3
4'd1: instr = {7'b0100000, 5'b00011, 5'b00010, 3'b000, 5'b00001, 7'b0110011};  // sub x1, x2, x3
4'd2: instr = {7'b0000001, 5'b00011, 5'b00010, 3'b000, 5'b00001, 7'b0110011};  // mul x1, x2, x3
4'd3: instr = {7'b0000001, 5'b00011, 5'b00010, 3'b100, 5'b00001, 7'b0110011};  // div x1, x2, x3
default: instr = 32'h00000000;
endcase
end
wire [6:0] opcode = instr[6:0];
wire [4:0] rd = instr[11:7];
wire [2:0] funct3 = instr[14:12];
wire [4:0] rs1 = instr[19:15];
wire [4:0] rs2 = instr[24:20];
wire [6:0] funct7 = instr[31:25];
wire [7:0] rv1 = regfile[rs1];
wire [7:0] rv2 = regfile[rs2];
reg [7:0] result;
always @(*) begin
result = 8'h00;
if (opcode == 7'b0110011) begin  // R-type
case (funct7)
7'b0000000: begin
if (funct3 == 3'b000) result = rv1 + rv2;  // ADD
end
7'b0100000: begin
if (funct3 == 3'b000) result = rv1 - rv2;  // SUB
end
7'b0000001: begin
if (funct3 == 3'b000) result = rv1 * rv2;  // MUL (low 8 bits)
if (funct3 == 3'b100) result = (rv2 != 0) ? rv1 / rv2 : 8'h00;  // DIV
end
default: result = 8'h00;
endcase
end
end
integer i;
always @(posedge clk) begin
if (!rst_n) begin
pc <= 4'd0;
for (i = 0; i < 16; i = i + 1) regfile[i] <= 8'h00;
regfile[2] <= 8'd4;  // x2 = 4
regfile[3] <= 8'd2;  // x3 = 2
end else begin
if (pc < 4'd4) pc <= pc + 4'd1;
if (rd != 5'b00000 && opcode == 7'b0110011) regfile[rd] <= result;
end
end
assign uo_out = regfile[1];  // Output the result in x1
endmodule
