# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

# Program: (Add ui_in + uio_in and output, then halt)
# 0x88: LOAD ui_in  -> x1
# 0x91: LOAD uio_in -> x2
# 0x1A: ADD x1, x2 -> x3
# 0xD8: STORE x3
# 0xFF: HALT

program = [
    0x88,  # 10001000: LOAD ui_in into x1
    0x91,  # 10010001: LOAD uio_in into x2
    0x1A,  # 00011010: ADD x1 and x2 -> x3
    0xD8,  # 11011000: STORE x3 to output
    0xFF,  # 11111111: HALT
] + [0x00]*11

async def load_program(dut, prog):
    """Write the user program (prog) to the instruction memory."""
    for addr, code in enumerate(prog):
        # High bit is write-enable, next 4 address, next 8 data
        loader_word = (1 << 7) | (addr << 3) | (code & 0xFF)
        dut.uio_in.value = loader_word
        await ClockCycles(dut.clk, 1)
    # Disable program-write after loading
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)

@cocotb.test()
async def test_addition_program(dut):
    """Test loading a program and performing addition."""
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset and clear everything
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Load program
    await load_program(dut, program)

    # Set input operands for addition (e.g., 15+7=22)
    dut.ui_in.value = 15
    dut.uio_in.value = 7

    # Give some time for CPU to execute
    await ClockCycles(dut.clk, 20)

    result = int(dut.uo_out.value)
    cpu_state = int(dut.uio_out.value) & 0x7
    dut._log.info(f"Addition Result: {result} (expected 22), CPU State: {cpu_state}")

    assert result == 22, f"Expected 22, got {result}"
    assert cpu_state == 4, f"Expected HALT state (4), got {cpu_state}"

    dut._log.info("Addition-only program test PASSED.")
