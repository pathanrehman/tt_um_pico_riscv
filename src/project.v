/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */
`default_nettype none
module tt_um_tiny_riscv (
    input  wire [7:0] ui_in,    // Dedicated inputs (user data in)
    output wire [7:0] uo_out,   // Dedicated outputs (user data out)
    input  wire [7:0] uio_in,   // User IOs: [7]=program_write_enable, [6:4]=program_write_addr, [3:0]=program_write_data
    output wire [7:0] uio_out,  // User IOs: output/debug
    output wire [7:0] uio_oe,   // IOs: output enable
    input  wire       ena,      // always 1 when design powered
    input  wire       clk,      // clock
    input  wire       rst_n     // active low reset
);

    // Tiny RISC-V Core Parameters
    parameter DATA_WIDTH = 8;
    parameter ADDR_WIDTH = 4;  // 16 instructions

    // CPU State
    reg [DATA_WIDTH-1:0] reg_file [0:7];  // 8 registers
    reg [ADDR_WIDTH-1:0] pc;              // Program counter
    reg [DATA_WIDTH-1:0] instruction;     // Current instruction
    reg [2:0] state;                      // CPU state machine

    // Writable instruction memory (RAM)
    reg [DATA_WIDTH-1:0] inst_mem [0:15];

    // Program loader signals mapped from uio_in
    wire program_write_enable = uio_in[7];
    wire [3:0] program_write_addr = uio_in[6:3];
    wire [7:0] program_write_data = {uio_in[3:0], 4'b0000}; // Lower 4 bits padded, change as needed

    // Instruction fields (8-bit simplified format)
    wire [1:0] opcode = instruction[7:6];
    wire [2:0] rd     = instruction[5:3];
    wire [2:0] rs2    = instruction[2:0];
    wire [2:0] imm3   = instruction[2:0];

    // Opcode definitions/ALU function codes
    parameter OP_ALU_REG = 2'b00, OP_ALU_IMM = 2'b01, OP_LOAD = 2'b10, OP_STORE = 2'b11;
    parameter ALU_ADD = 3'b000, ALU_SUB = 3'b001, ALU_AND = 3'b010, ALU_OR  = 3'b011;
    parameter ALU_XOR = 3'b100, ALU_SLL = 3'b101, ALU_SRL = 3'b110, ALU_MUL = 3'b111;
    parameter FETCH = 3'b000, DECODE=3'b001, EXECUTE=3'b010, WRITEBACK=3'b011, HALT=3'b100;

    // ALU
    reg [DATA_WIDTH-1:0] alu_a, alu_b, alu_result;
    reg [2:0] alu_op;

    always @(*) begin
        case (alu_op)
            ALU_ADD: alu_result = alu_a + alu_b;
            ALU_SUB: alu_result = alu_a - alu_b;
            ALU_AND: alu_result = alu_a & alu_b;
            ALU_OR:  alu_result = alu_a | alu_b;
            ALU_XOR: alu_result = alu_a ^ alu_b;
            ALU_SLL: alu_result = alu_a << alu_b[2:0];
            ALU_SRL: alu_result = alu_a >> alu_b[2:0];
            ALU_MUL: alu_result = alu_a[3:0] * alu_b[3:0];
            default: alu_result = 8'h00;
        endcase
    end

    // Output register for results
    reg [DATA_WIDTH-1:0] output_reg;

    // Main logic: adds a program loading phase before FETCH
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pc <= 4'h0;
            state <= FETCH;
            output_reg <= 8'h00;
            integer i;
            for (i = 0; i < 8; i = i+1)
                reg_file[i] <= 8'h00;
        end else begin
            if (program_write_enable) begin
                inst_mem[program_write_addr] <= program_write_data;
            end else begin
                case (state)
                    FETCH: begin
                        if (pc < 16) begin
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
                                alu_a <= reg_file[1];
                                alu_b <= reg_file[rs2];
                                alu_op <= rd;
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
                        if (rd != 3'b000) begin
                            reg_file[rd] <= alu_result;
                        end
                        pc <= pc + 1;
                        state <= FETCH;
                    end
                    HALT: begin
                        state <= HALT;
                    end
                    default: begin
                        state <= FETCH;
                    end
                endcase
            end
        end
    end

    // Outputs
    assign uo_out   = output_reg;
    assign uio_out  = {5'b0, state}; // show state in lower 3 bits
    assign uio_oe   = 8'b00011111;

    wire _unused = &{ena, 1'b0};
endmodule
