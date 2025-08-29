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
    await ClockCycles(dut.clk, 1)
    
    dut._log.info("Test project behavior")
    
    # Helper function to load a 16-bit instruction
    async def load_instruction(instruction):
        # Load lower byte first (bit 7 = load enable)
        lower_byte = (instruction & 0xFF) >> 1  # Right shift to fit in 7 bits
        dut.ui_in.value = 0x80 | lower_byte  # Set load enable (bit 7) + lower 7 bits
        await ClockCycles(dut.clk, 1)
        
        # Load upper byte
        upper_byte = (instruction >> 8) & 0xFF
        dut.uio_in.value = upper_byte
        dut.ui_in.value = 0x80 | lower_byte  # Keep load enable high
        await ClockCycles(dut.clk, 1)
        
        # Clear load enable to execute instruction
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, 1)
    
    # Test 1: Load Immediate (LI) instruction
    dut._log.info("Test 1: Load Immediate to register 1")
    # Instruction format: funct3[15:13]=111 (default for LI), imm[12:8]=5, rd[4:2]=1, opcode[1:0]=01
    # Binary: 111_00101_000_001_01 = 0xE505
    await load_instruction(0xE505)  # Load immediate value 5 into register 1
    
    # Check that register 1 contains 5 (should appear on uo_out since current_rd = 1)
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 5, f"Expected 5, got {dut.uo_out.value}"
    dut._log.info("✓ Load Immediate test passed")
    
    # Test 2: ADDI instruction
    dut._log.info("Test 2: Add Immediate")
    # ADDI r2, r1, 3: funct3=000, imm=3, rs1=1, rd=2, opcode=01
    # Binary: 000_00011_001_010_01 = 0x0325
    await load_instruction(0x0325)  # r2 = r1 + 3 = 5 + 3 = 8
    
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 8, f"Expected 8, got {dut.uo_out.value}"
    dut._log.info("✓ ADDI test passed")
    
    # Test 3: R-type ADD instruction
    dut._log.info("Test 3: R-type ADD")
    # Load another immediate first: LI r3, 7
    await load_instruction(0xE71D)  # Load 7 into r3
    await ClockCycles(dut.clk, 1)
    
    # ADD r4, r2, r3: funct3=000, rs2=3, rs1=2, rd=4, opcode=00
    # Binary: 000_011_010_100_00 = 0x0D20
    await load_instruction(0x0D20)  # r4 = r2 + r3 = 8 + 7 = 15
    
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 15, f"Expected 15, got {dut.uo_out.value}"
    dut._log.info("✓ R-type ADD test passed")
    
    # Test 4: SUB instruction
    dut._log.info("Test 4: R-type SUB")
    # SUB r5, r4, r1: funct3=001, rs2=1, rs1=4, rd=5, opcode=00
    # Binary: 001_001_100_101_00 = 0x2734
    await load_instruction(0x2734)  # r5 = r4 - r1 = 15 - 5 = 10
    
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 10, f"Expected 10, got {dut.uo_out.value}"
    dut._log.info("✓ R-type SUB test passed")
    
    # Test 5: AND instruction
    dut._log.info("Test 5: R-type AND")
    # Load 15 into r6: LI r6, 15
    await load_instruction(0xEF35)  # Load 15 into r6
    await ClockCycles(dut.clk, 1)
    
    # AND r7, r4, r6: funct3=010, rs2=6, rs1=4, rd=7, opcode=00
    # Binary: 010_110_100_111_00 = 0x5B3C
    await load_instruction(0x5B3C)  # r7 = r4 & r6 = 15 & 15 = 15
    
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 15, f"Expected 15, got {dut.uo_out.value}"
    dut._log.info("✓ R-type AND test passed")
    
    # Test 6: Branch Equal (BEQ)
    dut._log.info("Test 6: Branch Equal")
    # First check current PC value
    pc_before = (dut.uio_out.value >> 3) & 0x1F  # Extract PC from uio_out[7:3]
    
    # BEQ r4, r7, 2: funct3=000 (but only [1:0] matter for branch), imm=2, rs2=7, rs1=4, opcode=11
    # Since r4 = r7 = 15, branch should be taken
    # Binary: 000_00010_111_100_11 = 0x05F3
    await load_instruction(0x05F3)
    
    await ClockCycles(dut.clk, 1)
    pc_after = (dut.uio_out.value >> 3) & 0x1F
    expected_pc = (pc_before + 1 + 2) & 0x1F  # PC + 1 (normal) + 2 (branch offset)
    assert pc_after == expected_pc, f"Expected PC {expected_pc}, got {pc_after}"
    dut._log.info("✓ Branch Equal test passed")
    
    # Test 7: Branch Not Equal (BNE) - should not branch
    dut._log.info("Test 7: Branch Not Equal (no branch)")
    pc_before = (dut.uio_out.value >> 3) & 0x1F
    
    # BNE r4, r7, 5: funct3=001, imm=5, rs2=7, rs1=4, opcode=11
    # Since r4 = r7 = 15, branch should NOT be taken
    # Binary: 001_00101_111_100_11 = 0x2BF3
    await load_instruction(0x2BF3)
    
    await ClockCycles(dut.clk, 1)
    pc_after = (dut.uio_out.value >> 3) & 0x1F
    expected_pc = (pc_before + 1) & 0x1F  # Just PC + 1 (no branch)
    assert pc_after == expected_pc, f"Expected PC {expected_pc}, got {pc_after}"
    dut._log.info("✓ Branch Not Equal (no branch) test passed")
    
    # Test 8: Store operation (check output)
    dut._log.info("Test 8: Store operation")
    # Store r5 (value=10): opcode=10, we need to construct a store instruction
    # The exact format depends on implementation, but let's use:
    # funct3=000, rs2=5, rs1=0, rd=0, opcode=10
    # Binary: 000_00000_101_000_10 = 0x0142
    await load_instruction(0x0142)
    
    await ClockCycles(dut.clk, 1)
    # For store operations, uo_out should show rs2 value (register 5 = 10)
    assert dut.uo_out.value == 10, f"Expected 10 (store value), got {dut.uo_out.value}"
    dut._log.info("✓ Store operation test passed")
    
    # Test 9: XOR operation
    dut._log.info("Test 9: R-type XOR")
    # XOR r1, r4, r6: r1 = r4 ^ r6 = 15 ^ 15 = 0
    # funct3=100, rs2=6, rs1=4, rd=1, opcode=00
    # Binary: 100_110_100_001_00 = 0x9B04
    await load_instruction(0x9B04)
    
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 0, f"Expected 0 (15 XOR 15), got {dut.uo_out.value}"
    dut._log.info("✓ R-type XOR test passed")
    
    # Test 10: Set Less Than (SLT)
    dut._log.info("Test 10: Set Less Than")
    # SLT r2, r5, r4: r2 = (r5 < r4) = (10 < 15) = 1
    # funct3=111, rs2=4, rs1=5, rd=2, opcode=00
    # Binary: 111_100_101_010_00 = 0xF548
    await load_instruction(0xF548)
    
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 1, f"Expected 1 (10 < 15), got {dut.uo_out.value}"
    dut._log.info("✓ Set Less Than test passed")
    
    dut._log.info("All tests completed successfully!")

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
    assert (dut.uio_out.value & 0xF8) == 0, "PC should be 0 after reset"  # Check PC bits
    assert (dut.uio_out.value & 0x07) == 0, "current_rd should be 0 after reset"  # Check rd bits
    
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
    await ClockCycles(dut.clk, 1)
    
    # Clear load enable without providing upper byte
    dut.ui_in.value = 0x05  # Clear load enable
    await ClockCycles(dut.clk, 2)
    
    # No instruction should execute (instruction_valid should be 0)
    # We can't directly check internal signals, but the system should remain stable
    
    # Now do a complete instruction load
    dut.ui_in.value = 0x80  # Load enable only
    await ClockCycles(dut.clk, 1)
    
    dut.uio_in.value = 0xE5  # Upper byte
    await ClockCycles(dut.clk, 1)
    
    dut.ui_in.value = 0x00  # Clear load enable to execute
    await ClockCycles(dut.clk, 1)
    
    dut._log.info("✓ Instruction loading protocol test completed")
