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

    // Internal signals
    wire rst = !rst_n;
    
    // Instruction register - 16 bits total
    reg [15:0] instruction_reg;
    reg instruction_valid;
    
    // Core registers - 8 x 8-bit register file
    reg [7:0] registers [0:7];
    
    // Program counter - 8 bits for simplicity
    reg [7:0] pc;
    
    // Load state for instruction loading protocol
    reg load_state; // 0 = expecting lower byte, 1 = expecting upper byte
    
    // Instruction decode
    wire [1:0] opcode = instruction_reg[1:0];
    wire [2:0] rd = instruction_reg[4:2];
    wire [2:0] rs1 = instruction_reg[7:5];
    wire [2:0] rs2 = instruction_reg[10:8];
    wire [2:0] funct3 = instruction_reg[15:13];
    wire [4:0] imm = instruction_reg[12:8]; // 5-bit immediate
    
    // ALU signals
    reg [7:0] alu_result;
    wire [7:0] operand_a = registers[rs1];
    wire [7:0] operand_b = registers[rs2];
    wire [7:0] imm_extended = {3'b0, imm}; // Zero-extend immediate
    
    // Control signals
    reg branch_taken;
    reg [2:0] current_rd;
    
    // ALU implementation
    always @(*) begin
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
    end
    
    // Main CPU logic
    always @(posedge clk) begin
        if (rst) begin
            // Reset all registers and state
            registers[0] <= 8'b0;
            registers[1] <= 8'b0;
            registers[2] <= 8'b0;
            registers[3] <= 8'b0;
            registers[4] <= 8'b0;
            registers[5] <= 8'b0;
            registers[6] <= 8'b0;
            registers[7] <= 8'b0;
            
            instruction_reg <= 16'b0;
            instruction_valid <= 1'b0;
            load_state <= 1'b0;
            pc <= 8'b0;
            branch_taken <= 1'b0;
            current_rd <= 3'b0;
            
        end else begin
            // Instruction loading protocol
            if (ui_in[7]) begin // Load enable
                if (!load_state) begin
                    // Load lower 8 bits of instruction
                    instruction_reg[7:0] <= {ui_in[6], ui_in[5:0], 1'b0}; // Pad to 8 bits
                    load_state <= 1'b1;
                    instruction_valid <= 1'b0;
                end else begin
                    // Load upper 8 bits of instruction  
                    instruction_reg[15:8] <= uio_in[7:0];  // Use full uio_in
                    load_state <= 1'b0;
                    instruction_valid <= 1'b1;
                end
            end else if (instruction_valid) begin
                // Execute instruction
                instruction_valid <= 1'b0;
                current_rd <= rd;
                
                case (opcode)
                    2'b00: begin // R-type
                        if (rd != 3'b0) // Don't write to register 0
                            registers[rd] <= alu_result;
                        branch_taken <= 1'b0;
                        pc <= pc + 1'b1;
                    end
                    
                    2'b01: begin // I-type  
                        case (funct3)
                            3'b000: begin // ADDI
                                if (rd != 3'b0)
                                    registers[rd] <= operand_a + imm_extended;
                            end
                            3'b010: begin // SLTI  
                                if (rd != 3'b0)
                                    registers[rd] <= (operand_a < imm_extended) ? 8'b1 : 8'b0;
                            end
                            3'b011: begin // ANDI
                                if (rd != 3'b0)
                                    registers[rd] <= operand_a & imm_extended;
                            end
                            3'b100: begin // ORI
                                if (rd != 3'b0)
                                    registers[rd] <= operand_a | imm_extended;
                            end
                            default: begin // LI (Load Immediate)
                                if (rd != 3'b0)
                                    registers[rd] <= imm_extended;
                            end
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
                        
                        if (branch_taken) begin
                            pc <= pc + imm_extended;
                        end else begin
                            pc <= pc + 1'b1;
                        end
                    end
                    default: begin
                        branch_taken <= 1'b0;
                        pc <= pc + 1'b1;
                    end
                endcase
            end
        end
    end
    
    // Output assignments
    assign uo_out = (opcode == 2'b10) ? registers[rs2] : registers[current_rd];
    assign uio_out = {pc[4:0], current_rd}; // Debug: show PC and current register
    assign uio_oe = 8'b11111111; // All uio pins as outputs for debugging
    
    // List all unused inputs to prevent warnings
    wire _unused = &{ena, 1'b0};

endmodule
