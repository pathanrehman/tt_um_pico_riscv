# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

# PROGRAM: [LOAD ui_in -> x1, LOAD uio_in -> x2, ADD x1,x2->x3, STORE x3, SUB x1,x2->x4, STORE x4, HALT]
program = [
    0b10001000, # LOAD ui_in into x1   (opcode=2, rd=1, rs2=0)
    0b10010001, # LOAD uio_in into x2  (opcode=2, rd=2, rs2=1)
    0b00011010, # ADD x1, x2 -> x3     (opcode=0, rd=3, rs2=2)
    0b11011000, # STORE x3 to output   (opcode=3, rd=3, rs2=0)
    0b00100101, # SUB x1, x2 -> x4     (opcode=0, rd=4, rs2=1, ALU_SUB)
    0b11100000, # STORE x4 to output   (opcode=3, rd=4, rs2=0)
    0b11111111, # HALT                 (opcode=3, rd=7, rs2=7)
] + [0x00]*9

async def program_cpu(dut, program):
    """Upload RISC-V instructions via uio_in as loader."""
    for addr, inst in enumerate(program):
        # Write-enable high, address, instruction data
        dut.uio_in.value = ((1 << 7) | (addr << 3) | (inst & 0xFF))
        await ClockCycles(dut.clk, 1)
    # Disable loader after programming
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)

@cocotb.test()
async def test_project(dut):
    dut._log.info("Start test_project with loader")

    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await program_cpu(dut, program)

    # Helper for one addition/subtraction test
    async def run_and_check(ui_val, uio_val, expect_sum, expect_diff):
        dut.rst_n.value = 0
        dut.ui_in.value = 0
        dut.uio_in.value = 0
        await ClockCycles(dut.clk, 3)
        dut.rst_n.value = 1
        dut.ui_in.value = ui_val
        dut.uio_in.value = uio_val

        # Wait for addition result
        await ClockCycles(dut.clk, 8)
        add_res = int(dut.uo_out.value)
        dut._log.info(f"Test ({ui_val} + {uio_val}): observed add result = {add_res} (expect {expect_sum})")
        assert add_res == expect_sum, f"Addition fail: got {add_res}, expected {expect_sum}"

        # Wait for subtraction result
        await ClockCycles(dut.clk, 5)
        sub_res = int(dut.uo_out.value)
        dut._log.info(f"Test ({ui_val} - {uio_val}): observed sub result = {sub_res} (expect {expect_diff})")
        assert sub_res == expect_diff, f"Subtraction fail: got {sub_res}, expected {expect_diff}"

        # Wait for halt state to register
        await ClockCycles(dut.clk, 5)
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
    dut._log.info("Testing CPU State Transitions")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await program_cpu(dut, program)
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
