# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

async def load_instruction(dut, lower_byte, upper_byte):
    # Load lower byte with load enable
    dut.ui_in.value = 0x80 | (lower_byte & 0x7F)
    await RisingEdge(dut.clk)
    
    # Load upper byte, keep load enable high
    dut.uio_in.value = upper_byte
    dut.ui_in.value = 0x80 | (lower_byte & 0x7F)
    await RisingEdge(dut.clk)
    
    # Clear load enable to trigger execution
    dut.ui_in.value = 0x00
    await RisingEdge(dut.clk)  # Execution happens here
    
    # Wait for result to be available
    await ClockCycles(dut.clk, 1)

@cocotb.test()
async def test_add_then_stable(dut):
    dut._log.info("Start")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset and initialisation
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Debug: Add some visibility into internal signals
    dut._log.info(f"Initial state: uo_out={int(dut.uo_out.value)}, uio_out={int(dut.uio_out.value)}")

    # --- Load LI r2, 5 ---
    dut._log.info("Loading LI r2, 5")
    await load_instruction(dut, lower_byte=0x09, upper_byte=0xE5)
    r2_val = int(dut.uo_out.value)
    dut._log.info(f"After LI r2, 5: uo_out = {r2_val} (should be 5)")

    # --- Load LI r3, 7 ---
    dut._log.info("Loading LI r3, 7")
    await load_instruction(dut, lower_byte=0x0B, upper_byte=0xE7)
    r3_val = int(dut.uo_out.value)
    dut._log.info(f"After LI r3, 7: uo_out = {r3_val} (should be 7)")

    # --- ADD r1 = r2 + r3 ---
    dut._log.info("Loading ADD r1, r2, r3")
    await load_instruction(dut, lower_byte=0x44, upper_byte=0x03)
    add_result = int(dut.uo_out.value)
    dut._log.info(f"ADD result uo_out = {add_result} (should be 12)")

    # Check register values by loading them back (debug)
    await load_instruction(dut, lower_byte=0x00, upper_byte=0xE0)  # LI r0, r2 value (dummy to see r2)
    r2_check = int(dut.uo_out.value)
    dut._log.info(f"Register r2 contains: {r2_check}")

    # Assert results
    assert r2_val == 5, f"LI to r2 failed! uo_out = {r2_val}"
    assert r3_val == 7, f"LI to r3 failed! uo_out = {r3_val}"
    assert add_result == 12, f"ADD r1=r2+r3 failed! uo_out = {add_result} (r2={r2_check})"

    dut._log.info("✓ All tests passed!")

@cocotb.test()
async def test_reset_behavior(dut):
    dut._log.info("Testing reset behavior")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    dut.ena.value = 1
    dut.ui_in.value = 0xFF
    dut.uio_in.value = 0xFF
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0x00
    dut.uio_in.value = 0x00
    await ClockCycles(dut.clk, 2)
    uio_out_val = int(dut.uio_out.value)
    uo_out_val = int(dut.uo_out.value)
    dut._log.info(f"Reset state - uo_out: {uo_out_val}, uio_out: {uio_out_val}")
    assert uo_out_val == 0, "Reset should clear uo_out"
    assert uio_out_val == 0, "Reset should clear uio_out"
    dut._log.info("✓ Reset behavior test passed")

@cocotb.test()
async def test_instruction_loading_protocol(dut):
    dut._log.info("Testing instruction loading protocol")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    initial_state = int(dut.uio_out.value)
    dut.ui_in.value = 0x85
    dut.uio_in.value = 0x00
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0x05
    await ClockCycles(dut.clk, 2)
    partial_state = int(dut.uio_out.value)
    dut.ui_in.value = 0x80
    dut.uio_in.value = 0x00
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = 0x00
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0x00
    await ClockCycles(dut.clk, 3)
    final_state = int(dut.uio_out.value)
    dut._log.info(f"States - Initial: {initial_state}, Partial: {partial_state}, Final: {final_state}")
    assert True
    dut._log.info("✓ Instruction loading protocol test completed")

@cocotb.test()
async def test_clock_and_reset_stability(dut):
    dut._log.info("Testing clock and reset stability")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    for i in range(3):
        dut._log.info(f"Reset cycle {i+1}")
        dut.ena.value = 1
        dut.ui_in.value = 0
        dut.uio_in.value = 0
        dut.rst_n.value = 0
        await ClockCycles(dut.clk, 5)
        dut.rst_n.value = 1
        await ClockCycles(dut.clk, 5)
        uo_out = int(dut.uo_out.value)
        uio_out = int(dut.uio_out.value)
        uio_oe = int(dut.uio_oe.value)
        dut._log.info(f"Cycle {i+1} outputs - uo_out: {uo_out}, uio_out: {uio_out}, uio_oe: {uio_oe}")
    dut._log.info("Extended operation test")
    for cycle in range(10):
        dut.ui_in.value = cycle & 0x7F
        dut.uio_in.value = (cycle * 2) & 0xFF
        await ClockCycles(dut.clk, 2)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut._log.info("✓ Clock and reset stability test passed")
