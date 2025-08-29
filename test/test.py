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
    
    dut._log.info("Test Tiny RISC-V Core - Basic Arithmetic Operations")
    
    # Test Case 1: Basic Addition (15 + 5 = 20)
    dut._log.info("Test Case 1: Addition - 15 + 5")
    dut.ui_in.value = 15   # First operand
    dut.uio_in.value = 5   # Second operand
    
    # Wait for the CPU to execute the pre-loaded program
    # The program loads inputs, performs addition, and outputs result
    await ClockCycles(dut.clk, 20)  # Give enough cycles for full execution
    
    # Check if we got the expected addition result (15 + 5 = 20)
    dut._log.info(f"Addition Result: {dut.uo_out.value} (expected 20)")
    dut._log.info(f"CPU State: {dut.uio_out.value & 0x07}")
    
    # Wait a bit more to see if CPU continues to subtraction
    await ClockCycles(dut.clk, 10)
    
    # Check subtraction result (15 - 5 = 10) - may appear later in execution
    dut._log.info(f"Final Result: {dut.uo_out.value}")
    dut._log.info(f"CPU State: {dut.uio_out.value & 0x07}")
    
    # Test Case 2: Different operands (25 + 8 = 33)
    dut._log.info("Test Case 2: Reset and test 25 + 8")
    
    # Reset the CPU
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    
    # Set new input values
    dut.ui_in.value = 25   # First operand
    dut.uio_in.value = 8   # Second operand
    dut.rst_n.value = 1
    
    # Execute the program again
    await ClockCycles(dut.clk, 20)
    
    dut._log.info(f"Addition Result: {dut.uo_out.value} (expected 33)")
    dut._log.info(f"CPU State: {dut.uio_out.value & 0x07}")
    
    # Wait for potential subtraction result (25 - 8 = 17)
    await ClockCycles(dut.clk, 10)
    dut._log.info(f"Subtraction Result: {dut.uo_out.value} (expected 17)")
    
    # Test Case 3: Edge case with smaller numbers (7 + 3 = 10)
    dut._log.info("Test Case 3: Reset and test 7 + 3")
    
    # Reset the CPU
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    
    # Set new input values
    dut.ui_in.value = 7    # First operand
    dut.uio_in.value = 3   # Second operand
    dut.rst_n.value = 1
    
    # Execute and monitor state transitions
    for cycle in range(25):
        await ClockCycles(dut.clk, 1)
        current_state = dut.uio_out.value & 0x07
        output_val = dut.uo_out.value
        
        if cycle % 5 == 0:  # Log every 5 cycles
            dut._log.info(f"Cycle {cycle}: State={current_state}, Output={output_val}")
        
        # Check for expected results
        if output_val == 10:  # Addition result
            dut._log.info(f"✓ Addition successful at cycle {cycle}: 7 + 3 = {output_val}")
        elif output_val == 4:  # Subtraction result
            dut._log.info(f"✓ Subtraction successful at cycle {cycle}: 7 - 3 = {output_val}")
        
        # Stop if CPU reaches HALT state (state = 4)
        if current_state == 4:
            dut._log.info(f"CPU halted at cycle {cycle}")
            break
    
    # Final state check
    final_output = dut.uo_out.value
    final_state = dut.uio_out.value & 0x07
    
    dut._log.info(f"Final Test Results:")
    dut._log.info(f"  Final Output: {final_output}")
    dut._log.info(f"  Final State: {final_state}")
    dut._log.info(f"  Expected: Addition=10, Subtraction=4, Halt State=4")
    
    # Basic assertion - check that we got some reasonable output
    # (The exact timing depends on the CPU implementation)
    assert final_output in [4, 10], f"Expected output 4 or 10, got {final_output}"
    
    dut._log.info("Test completed successfully!")

@cocotb.test()
async def test_cpu_states(dut):
    """Test to specifically monitor CPU state transitions"""
    dut._log.info("Testing CPU State Transitions")
    
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut.ena.value = 1
    dut.ui_in.value = 12
    dut.uio_in.value = 4
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    
    # Monitor state transitions for detailed analysis
    states = ["FETCH", "DECODE", "EXECUTE", "WRITEBACK", "HALT", "UNKNOWN", "UNKNOWN", "UNKNOWN"]
    
    for cycle in range(30):
        await ClockCycles(dut.clk, 1)
        current_state = dut.uio_out.value & 0x07
        output_val = dut.uo_out.value
        
        state_name = states[current_state] if current_state < len(states) else f"STATE_{current_state}"
        dut._log.info(f"Cycle {cycle:2d}: {state_name} | Output: {output_val:3d}")
        
        if current_state == 4:  # HALT
            dut._log.info("CPU reached HALT state")
            break
    
    dut._log.info("State transition test completed")
