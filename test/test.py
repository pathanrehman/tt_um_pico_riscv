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

    # Helper: run sequence, check both addition and subtraction outputs
    async def run_and_check(first_val, second_val, expect_sum, expect_diff):
        # Reset
        dut.ena.value = 1
        dut.ui_in.value = 0
        dut.uio_in.value = 0
        dut.rst_n.value = 0
        await ClockCycles(dut.clk, 8)
        dut.rst_n.value = 1

        dut.ui_in.value = first_val
        dut.uio_in.value = second_val

        # Wait for ADD & store to output (program: 8 ops, multi-cycle FSM)
        await ClockCycles(dut.clk, 14)
        addition_result = int(dut.uo_out.value)
        cpu_state_add = int(dut.uio_out.value) & 0x07
        dut._log.info(f"After ADD, uo_out: {addition_result} (expected {expect_sum}), state={cpu_state_add}")

        # Wait more for SUB & store to output
        await ClockCycles(dut.clk, 5)
        subtraction_result = int(dut.uo_out.value)
        cpu_state_sub = int(dut.uio_out.value) & 0x07
        dut._log.info(f"After SUB, uo_out: {subtraction_result} (expected {expect_diff}), state={cpu_state_sub}")

        # Wait for HALT
        await ClockCycles(dut.clk, 5)
        halt_state = int(dut.uio_out.value) & 0x07
        dut._log.info(f"Final state (expect HALT=4): {halt_state}")

        assert addition_result == expect_sum,      f"Addition fail: got {addition_result}, expected {expect_sum}"
        assert subtraction_result == expect_diff,  f"Subtraction fail: got {subtraction_result}, expected {expect_diff}"
        assert halt_state == 4,                    f"CPU did not halt as expected, got state {halt_state}"

    # Test Case 1: 15 + 5 = 20, 15 - 5 = 10
    await run_and_check(15, 5, 20, 10)

    # Test Case 2: 25 + 8 = 33, 25 - 8 = 17
    await run_and_check(25, 8, 33, 17)

    # Test Case 3: 7 + 3 = 10, 7 - 3 = 4
    await run_and_check(7, 3, 10, 4)

    # Edge case: 12 + 4 = 16, 12 - 4 = 8
    await run_and_check(12, 4, 16, 8)

    dut._log.info("All test cases PASSED.")

@cocotb.test()
async def test_cpu_states(dut):
    """Test to specifically monitor CPU state transitions"""
    dut._log.info("Testing CPU State Transitions")

    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 12
    dut.uio_in.value = 4
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    states = ["FETCH", "DECODE", "EXECUTE", "WRITEBACK", "HALT", "UNKNOWN", "UNKNOWN", "UNKNOWN"]

    for cycle in range(30):
        await ClockCycles(dut.clk, 1)
        current_state = int(dut.uio_out.value) & 0x07
        output_val = int(dut.uo_out.value)

        state_name = states[current_state] if current_state < len(states) else f"STATE_{current_state}"
        dut._log.info(f"Cycle {cycle:2d}: {state_name} | Output: {output_val:3d}")

        if current_state == 4:  # HALT
            dut._log.info("CPU reached HALT state")
            break

    dut._log.info("State transition test completed")
