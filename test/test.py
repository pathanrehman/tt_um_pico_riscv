# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

# ADDITION PROGRAM ENCODING:
# 0: LOAD ui_in -> x1      (opcode=2, rd=1, rs2=0)  = 0b10_001_000 = 0x48
# 1: LOAD uio_in -> x2     (opcode=2, rd=2, rs2=1)  = 0b10_010_001 = 0x91
# 2: ADD x1, x2 -> x3      (opcode=0, rd=3, rs2=2)  = 0b00_011_010 = 0x1A
# 3: STORE x3 to out       (opcode=3, rd=3, rs2=0)  = 0b11_011_000 = 0xD8
# 4: HALT                  (opcode=3, rd=7, rs2=7)  = 0b11_111_111 = 0xFF

program = [0x48, 0x91, 0x1A, 0xD8, 0xFF] + [0x00]*11  # Fill 16 instruction slots

async def load_program(dut, prog):
    """Write the user program into instruction memory via uio_in."""
    for addr, code in enumerate(prog):
        # Set write enable (bit 7), address (bits 6:3), data (bits 2:0 of code)
        uio_val = (1<<7) | ((addr & 0xF) << 3) | ((code >> 4) & 0x07)
        dut.uio_in.value = uio_val
        await ClockCycles(dut.clk, 1)
        # Now set lower bits and keep write enable
        uio_val = (1<<7) | ((addr & 0xF) << 3) | (code & 0x07)
        dut.uio_in.value = uio_val
        await ClockCycles(dut.clk, 1)
    # Clear write enable to allow CPU execution
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)

@cocotb.test()
async def test_addition_program(dut):
    dut._log.info("Start test_addition_program")

    # Setup clock
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    # Upload addition-only program
    await load_program(dut, program)
    dut._log.info("Addition program uploaded")

    # Test addition of 15 + 7
    dut.ui_in.value = 15
    dut.uio_in.value = 7

    # Wait for the CPU to execute (program length + margin)
    await ClockCycles(dut.clk, 20)

    result = int(dut.uo_out.value)
    cpu_state = int(dut.uio_out.value) & 0x7
    dut._log.info(f"Addition Result: {result} (expected 22), CPU State: {cpu_state}")
    assert result == 22, f"Expected 22, got {result}"
    assert cpu_state == 4, f"Expected HALT state (4), got {cpu_state}"

    dut._log.info("Addition-only program test PASSED.")
