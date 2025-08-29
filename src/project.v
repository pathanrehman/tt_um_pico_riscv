/*
 * Copyright (c) 2025 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */
`default_nettype none
module tt_um_pico_riscv (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
    // Internal active-high reset
    wire rst = ~rst_n;

    // State machine states
    localparam IDLE = 2'b00;
    localparam LOAD = 2'b01;
    localparam EXECUTE = 2'b10;
    reg [1:0] state;
    reg [1:0] reset_count; // Reset hold-off counter

    // Instruction register - 16 bits total
    reg [15:0] instruction_reg;
    reg [15:0] instruction_exec; // Execution stage
    reg [2:0]  current_rd;       // Current destination register
    reg [2:0]  current_rd_delayed; // Delayed for output

    // 8 x 8-bit register file
    reg [7:0] registers [0:7];
    reg [7:0] pc;
    reg       branch_taken;

    // ALU result
    reg [7:0] alu_result;

    // Instruction decode (from execution stage)
    wire [1:0] opcode   = instruction_exec[1:0];
    wire [2:0] rd       = instruction_exec[4:2];
    wire [2:0] rs1      = instruction_exec[7:5];
    wire [2:0] rs2      = instruction_exec[10:8];
    wire [2:0] funct3   = instruction_exec[15:13];
    wire [4:0] imm      = instruction_exec[12:8];    // 5-bit immediate

    wire [7:0] operand_a     = registers[rs1];
    wire [7:0] operand_b     = registers[rs2];
    wire [7:0] imm_extended  = {3'b0, imm};

    // Reset and state machine
    integer i;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            for (i = 0; i < 8; i = i + 1)
                registers[i] <= 8'b0;
            instruction_reg <= 16'b0;
            instruction_exec <= 16'b0;
            current_rd <= 3'b0;
            current_rd_delayed <= 3'b0;
            pc <= 8'b0;
            branch_taken <= 1'b0;
            state <= IDLE;
            reset_count <= 2'b11; // Hold-off for 3 cycles
        end else begin
            // Reset hold-off
            if (reset_count != 0) begin
                reset_count <= reset_count - 1;
                state <= IDLE;
            end else begin
                case (state)
                    IDLE: begin
                        if (ui_in[7] && ena) begin // Load enable
                            instruction_reg <= {uio_in[7:0], ui_in[6:0]};
                            state <= LOAD;
                        end
                    end
                    LOAD: begin
                        instruction_exec <= instruction_reg;
                        state <= EXECUTE;
                    end
                    EXECUTE: begin
                        // ALU operation
                        case (funct3)
                            3'b000: alu_result = operand_a + operand_b;      // ADD
                            3'b001: alu_result = operand_a - operand_b;      // SUB  
                            3'b010: alu_result = operand_a & operand_b;      // AND
                            3'b011: alu_result = operand_a | operand_b;      // OR
                            3'b100: alu_result = operand_a ^ operand_b;      // XOR
                            3'b101: alu_result = operand_a << operand_b[2:0]; // SLL
                            3'b110: alu_result = operand_a >> operand_b[2:0]; // SRL
                            3'b111: alu_result = (operand_a < operand_b) ? 8'b1 : 8'b0; // SLT
                            default: alu_result = 8'b0;
                        endcase

                        // Decoder
                        case (opcode)
                            2'b00: begin // R-type
                                if (rd != 3'b000)
                                    registers[rd] <= alu_result;
                                branch_taken <= 1'b0;
                                pc <= pc + 1'b1;
                            end
                            2'b01: begin // I-type
                                case (funct3)
                                    3'b000: if (rd != 3'b000) registers[rd] <= operand_a + imm_extended; // ADDI
                                    3'b010: if (rd != 3'b000) registers[rd] <= (operand_a < imm_extended) ? 8'b1 : 8'b0; // SLTI
                                    3'b011: if (rd != 3'b000) registers[rd] <= operand_a & imm_extended; // ANDI
                                    3'b100: if (rd != 3'b000) registers[rd] <= operand_a | imm_extended; // ORI
                                    default: if (rd != 3'b000) registers[rd] <= imm_extended; // Load Immediate
                                endcase
                                branch_taken <= 1'b0;
                                pc <= pc + 1'b1;
                            end
                            2'b10: begin // S-type (Store)
                                branch_taken <= 1'b0;
                                pc <= pc + 1'b1;
                            end
                            2'b11: begin // B-type (Branch)
                                case (funct3[1:0])
                                    2'b00: branch_taken <= (operand_a == operand_b);
                                    2'b01: branch_taken <= (operand_a != operand_b);
                                    2'b10: branch_taken <= (operand_a < operand_b);
                                    2'b11: branch_taken <= (operand_a >= operand_b);
                                endcase
                                if (branch_taken) pc <= pc + imm_extended;
                                else pc <= pc + 1'b1;
                            end
                            default: begin
                                branch_taken <= 1'b0;
                                pc <= pc + 1'b1;
                            end
                        endcase
                        current_rd <= rd;
                        current_rd_delayed <= rd; // Update in EXECUTE
                        state <= IDLE;
                    end
                    default: state <= IDLE;
                endcase
            end
        end
    end

    // Output assignments
    assign uo_out  = registers[current_rd_delayed]; // Always use delayed rd
    assign uio_out = {4'b0, current_rd_delayed}; // Debug: show current_rd_delayed
    assign uio_oe  = 8'b11111111; // All outputs enabled

    // Prevent warnings on unused input
    wire _unused = &{ena, 1'b0};
endmodule
