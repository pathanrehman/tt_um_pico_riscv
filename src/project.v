/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */
`default_nettype none
module tt_um_tiny_riscv (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
    parameter DATA_WIDTH = 8;
    parameter ADDR_WIDTH = 4;  // 16 locations for instructions/data

    reg [DATA_WIDTH-1:0] reg_file [0:7];  // 8 registers (x0-x7)
    reg [ADDR_WIDTH-1:0] pc;               // Program counter
    reg [DATA_WIDTH-1:0] instruction;      // Current instruction
    reg [2:0] state;                       // CPU state machine

    // Instruction fields (8-bit simplified format)
    // [7:6] - opcode, [5:3] - rd/rs1, [2:0] - rs2/immediate
    wire [1:0] opcode = instruction[7:6];
    wire [2:0] rd     = instruction[5:3];
    wire [2:0] rs2    = instruction[2:0];
    wire [2:0] imm3   = instruction[2:0];  // 3-bit immediate

    // Opcode definitions
    parameter OP_ALU_REG = 2'b00;  // Register-register ALU ops
    parameter OP_ALU_IMM = 2'b01;  // Register-immediate ALU ops  
    parameter OP_LOAD    = 2'b10;  // Load from input
    parameter OP_STORE   = 2'b11;  // Store to output

    // ALU function codes (using rd field when opcode is ALU)
    parameter ALU_ADD = 3'b000;
    parameter ALU_SUB = 3'b001;
    parameter ALU_AND = 3'b010;
    parameter ALU_OR  = 3'b011;
    parameter ALU_XOR = 3'b100;
    parameter ALU_SLL = 3'b101;  // Shift left logical
    parameter ALU_SRL = 3'b110;  // Shift right logical
    parameter ALU_MUL = 3'b111;  // Simple multiplication

    // State machine states
    parameter FETCH   = 3'b000;
    parameter DECODE  = 3'b001;
    parameter EXECUTE = 3'b010;
    parameter WRITEBACK = 3'b011;
    parameter HALT    = 3'b100;

    reg [DATA_WIDTH-1:0] inst_mem [0:15];
    reg [DATA_WIDTH-1:0] alu_a, alu_b, alu_result;
    reg [2:0] alu_op;
    integer i;

    always @(*) begin
        case (alu_op)
            ALU_ADD: alu_result = alu_a + alu_b;
            ALU_SUB: alu_result = alu_a - alu_b;
            ALU_AND: alu_result = alu_a & alu_b;
            ALU_OR:  alu_result = alu_a | alu_b;
            ALU_XOR: alu_result = alu_a ^ alu_b;
            ALU_SLL: alu_result = alu_a << alu_b[2:0];
            ALU_SRL: alu_result = alu_a >> alu_b[2:0];
            ALU_MUL: alu_result = alu_a[3:0] * alu_b[3:0]; // 4x4=8 bit multiply
            default: alu_result = 8'h00;
        endcase
    end

    reg [DATA_WIDTH-1:0] output_reg;

    // Initialize instruction memory with a test program (ADDITION + SUBTRACTION)
    initial begin
        inst_mem[0]  = 8'b10_001_000; // LOAD ui_in[7:0] to x1
        inst_mem[1]  = 8'b10_010_001; // LOAD uio_in[7:0] to x2
        inst_mem[2]  = 8'b00_011_010; // ADD x1, x2 -> x3 (rd=3, rs2=2 encoded)
        inst_mem[3]  = 8'b11_011_000; // STORE x3 to output
        inst_mem[4]  = 8'b00_100_001; // SUB x1, x2 -> x4 (rd=4, alu_op=SUB)
        inst_mem[5]  = 8'b11_100_000; // STORE x4 to output
        inst_mem[6]  = 8'b11_111_111; // HALT

        // Zero out rest for clean simulation
        for (i = 7; i < 16; i = i + 1)
            inst_mem[i] = 8'h00;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pc <= 4'h0;
            state <= FETCH;
            output_reg <= 8'h00;
            for (i = 0; i < 8; i = i + 1)
                reg_file[i] <= 8'h00;
        end else begin
            case (state)
                FETCH: begin
                    if (pc < 4'd16) begin
                        instruction <= inst_mem[pc];
                        state <= DECODE;
                    end else begin
                        state <= HALT;
                    end
                end

                DECODE: begin
                    state <= EXECUTE;
                end

                EXECUTE: begin
                    case (opcode)
                        OP_ALU_REG: begin
                            alu_a <= reg_file[1];   // always x1 as src1
                            alu_b <= reg_file[rs2];
                            alu_op <= rd;           // use rd as ALU function
                            state <= WRITEBACK;
                        end

                        OP_ALU_IMM: begin
                            alu_a <= reg_file[1];
                            alu_b <= {5'b0, imm3};
                            alu_op <= rd;
                            state <= WRITEBACK;
                        end

                        OP_LOAD: begin
                            case (rs2[0])
                                1'b0: reg_file[rd] <= ui_in;
                                1'b1: reg_file[rd] <= uio_in;
                            endcase
                            pc <= pc + 1;
                            state <= FETCH;
                        end

                        OP_STORE: begin
                            if (rd == 3'b111) begin
                                state <= HALT;
                            end else begin
                                output_reg <= reg_file[rd];
                                pc <= pc + 1;
                                state <= FETCH;
                            end
                        end

                        default: begin
                            pc <= pc + 1;
                            state <= FETCH;
                        end
                    endcase
                end

                WRITEBACK: begin
                    // Write ALU result back to register (except x0)
                    if (rd != 3'b000)
                        reg_file[rd] <= alu_result;
                    pc <= pc + 1;
                    state <= FETCH;
                end

                HALT: state <= HALT;
                default: state <= FETCH;
            endcase
        end
    end

    assign uo_out = output_reg;
    assign uio_out = {5'b0, state};
    assign uio_oe = 8'b00011111;
    wire _unused = &{ena, 1'b0};
endmodule
