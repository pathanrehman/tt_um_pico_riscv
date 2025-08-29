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

    # Helper for one addition/subtraction test
    async def run_and_check(ui_val, uio_val, expect_sum, expect_diff):
        dut.rst_n.value = 0
        dut.ui_in.value = 0
        dut.uio_in.value = 0
        await ClockCycles(dut.clk, 3)
        dut.rst_n.value = 1

        dut.ui_in.value = ui_val
        dut.uio_in.value = uio_val

        # WAIT for addition result (program: fill, add, store = 4+ cycles); add margin
        await ClockCycles(dut.clk, 8)
        add_res = int(dut.uo_out.value)
        dut._log.info(f"Test ({ui_val} + {uio_val}): observed add result = {add_res} (expect {expect_sum})")
        assert add_res == expect_sum, f"Addition fail: got {add_res}, expected {expect_sum}"

        # WAIT for subtraction result (needs another store); add margin
        await ClockCycles(dut.clk, 5)
        sub_res = int(dut.uo_out.value)
        dut._log.info(f"Test ({ui_val} - {uio_val}): observed sub result = {sub_res} (expect {expect_diff})")
        assert sub_res == expect_diff, f"Subtraction fail: got {sub_res}, expected {expect_diff}"

        # Wait for halt to be observed if you want
        await ClockCycles(dut.clk, 7)
        cpu_state = int(dut.uio_out.value) & 0x7
        dut._log.info(f"CPU final state: {cpu_state} (expect 4 for HALT)")
        assert cpu_state == 4, f"CPU did not reach HALT state (got {cpu_state})"

    # Run several tests
    await run_and_check(15, 5, 20, 10)
    await run_and_check(25, 8, 33, 17)
    await run_and_check(7, 3, 10, 4)
    await run_and_check(12, 4, 16, 8)

    dut._log.info("All test cases PASSED.")

@cocotb.test()
async def test_cpu_states(dut):
    """Test CPU state transitions for verification."""
    dut._log.info("Testing CPU State Transitions")

    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 12
    dut.uio_in.value = 4
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

    states = ["FETCH", "DECODE", "EXECUTE", "WRITEBACK", "HALT", "?", "?", "?"]

    for cycle in range(30):
        await ClockCycles(dut.clk, 1)
        current_state = int(dut.uio_out.value) & 0x07
        output_val = int(dut.uo_out.value)
        state_name = states[current_state] if current_state < len(states) else f"{current_state}"
        dut._log.info(f"Cycle {cycle:2d}: {state_name} | Output: {output_val:3d}")
        if current_state == 4:
            dut._log.info("CPU reached HALT state")
            break

    dut._log.info("State transition test completed")
