# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")
    
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    
    dut._log.info("Test project behavior")
    
    # Helper function to load a 16-bit instruction
    async def load_instruction(instruction):
        dut._log.info(f"Loading instruction 0x{instruction:04X}")
        
        # Load lower byte first (bit 7 = load enable)
        # The Verilog code takes ui_in[6:0] and pads with 1'b0, so we need 7 bits
        lower_7bits = instruction & 0x7F
        dut.ui_in.value = 0x80 | lower_7bits  # Set load enable (bit 7) + lower 7 bits
        dut.uio_in.value = 0  # Clear uio_in for first phase
        await ClockCycles(dut.clk, 1)
        
        # Load upper byte 
        upper_byte = (instruction >> 8) & 0xFF
        dut.uio_in.value = upper_byte
        # Keep load enable high and same lower bits
        dut.ui_in.value = 0x80 | lower_7bits
        await ClockCycles(dut.clk, 1)
        
        # Clear load enable to execute instruction
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, 1)
        
        dut._log.info(f"Instruction loaded, uo_out = {dut.uo_out.value}")
    
    # Test 1: Load Immediate (LI) instruction
    dut._log.info("Test 1: Load Immediate to register 1")
    # Instruction format for LI: opcode[1:0]=01 (I-type), rd[4:2]=001, imm[12:8]=00101 (5), funct3[15:13]=111 (default for LI)
    # Binary: 111_00101_xxx_001_01
    # Let's use: 111_00101_000_001_01 = 0xE505
    # But we need to be careful about the bit layout in the Verilog code
    
    # According to Verilog: instruction_reg[7:0] gets {ui_in[6], ui_in[5:0], 1'b0}
    # So lower 7 bits of ui_in become bits [7:1] of instruction_reg[7:0], bit 0 is always 0
    # This means our instruction needs to be shifted
    
    # Let's try a simpler approach - Load immediate 5 into register 1
    # I-type: opcode=01, rd=001, rs1=000, imm=00101, funct3=111 (for default LI)
    # Full instruction: 111_00101_000_001_01 = binary
    # In hex: 0xE505, but we need to account for the bit shifting in load protocol
    
    instruction = 0xE50A  # Adjusted for the bit shifting in load protocol
    await load_instruction(instruction)
    
    # Wait a bit more for instruction to execute
    await ClockCycles(dut.clk, 2)
    
    # Check that register 1 contains 5 (should appear on uo_out since current_rd = 1)
    expected = 5
    actual = int(dut.uo_out.value)
    dut._log.info(f"Expected: {expected}, Actual: {actual}")
    assert actual == expected, f"Expected {expected}, got {actual}"
    dut._log.info("✓ Load Immediate test passed")
    
    # Test 2: Load Immediate with different value
    dut._log.info("Test 2: Load Immediate 10 to register 2")
    # LI r2, 10: opcode=01, rd=010, imm=01010, funct3=111
    instruction = 0xEA8A  # Adjusted encoding
    await load_instruction(instruction)
    await ClockCycles(dut.clk, 2)
    
    expected = 10
    actual = int(dut.uo_out.value)
    dut._log.info(f"Expected: {expected}, Actual: {actual}")
    assert actual == expected, f"Expected {expected}, got {actual}"
    dut._log.info("✓ Second Load Immediate test passed")
    
    # Test 3: ADDI instruction
    dut._log.info("Test 3: Add Immediate")
    # ADDI r3, r2, 3: opcode=01, rd=011, rs1=010, imm=00011, funct3=000
    instruction = 0x0D1E  # Adjusted encoding
    await load_instruction(instruction)
    await ClockCycles(dut.clk, 2)
    
    expected = 13  # 10 + 3
    actual = int(dut.uo_out.value)
    dut._log.info(f"Expected: {expected}, Actual: {actual}")
    assert actual == expected, f"Expected {expected}, got {actual}"
    dut._log.info("✓ ADDI test passed")
    
    dut._log.info("Basic tests completed successfully!")

@cocotb.test()
async def test_reset_behavior(dut):
    """Test that reset properly initializes all registers"""
    dut._log.info("Testing reset behavior")
    
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    
    # Set some non-zero inputs
    dut.ena.value = 1
    dut.ui_in.value = 0xFF
    dut.uio_in.value = 0xFF
    
    # Apply reset
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    
    # Release reset
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    
    # Check that outputs are in reset state
    # PC should be 0, current_rd should be 0
    uio_out_val = int(dut.uio_out.value)
    pc_bits = (uio_out_val >> 3) & 0x1F  # Extract PC from bits [7:3]
    rd_bits = uio_out_val & 0x07         # Extract rd from bits [2:0]
    
    assert pc_bits == 0, f"PC should be 0 after reset, got {pc_bits}"
    assert rd_bits == 0, f"current_rd should be 0 after reset, got {rd_bits}"
    
    dut._log.info("✓ Reset behavior test passed")

@cocotb.test()  
async def test_instruction_loading_protocol(dut):
    """Test the two-phase instruction loading protocol"""
    dut._log.info("Testing instruction loading protocol")
    
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    
    # Test incomplete instruction loading (only lower byte)
    dut.ui_in.value = 0x85  # Load enable + some data
    dut.uio_in.value = 0x00
    await ClockCycles(dut.clk, 1)
    
    # Clear load enable without providing upper byte
    dut.ui_in.value = 0x05  # Clear load enable
    await ClockCycles(dut.clk, 2)
    
    # Outputs should remain stable (no instruction execution)
    initial_uo_out = int(dut.uo_out.value)
    
    # Now do a complete instruction load (NOP-like instruction)
    dut.ui_in.value = 0x80  # Load enable + zero data
    dut.uio_in.value = 0x00
    await ClockCycles(dut.clk, 1)
    
    dut.uio_in.value = 0x00  # Upper byte = 0
    await ClockCycles(dut.clk, 1)
    
    dut.ui_in.value = 0x00  # Clear load enable to execute
    await ClockCycles(dut.clk, 2)
    
    dut._log.info("✓ Instruction loading protocol test completed")
