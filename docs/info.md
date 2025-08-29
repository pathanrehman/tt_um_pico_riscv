# PicoRISC-V Educational Core

## How it works

PicoRISC-V is a minimal 8-bit RISC-V processor core designed specifically for educational purposes and optimized for Tiny Tapeout's 160x100 μm area constraints. The core implements a simplified RISC-V instruction set with 16-bit compressed instructions to maximize educational value while fitting within a single tile.

### Architecture Features

**8-bit Datapath**: Uses 8-bit registers and ALU operations instead of the standard 32-bit RISC-V implementation, making it easier to understand and trace execution manually.

**Compressed Instructions**: Implements 16-bit instructions based on the RISC-V compressed extension (RVC) to reduce instruction decode complexity and save area.

**Minimal Register File**: Contains 8 general-purpose registers (R0-R7) instead of the standard 32 registers. Register R0 is hardwired to zero following RISC-V conventions.

**Single-Cycle Execution**: Each instruction executes in one clock cycle for educational simplicity, with no pipeline complexity.

**Instruction Set**: Supports four instruction types:
- **R-Type**: Register-to-register operations (ADD, SUB, AND, OR, XOR, SLL, SRL, SLT)
- **I-Type**: Immediate operations (ADDI, SLTI, ANDI, ORI, LI)
- **S-Type**: Store operations (outputs register values to pins)
- **B-Type**: Branch operations (BEQ, BNE, BLT, BGE)

### Instruction Format (16-bit)

[15:13] [12:8] [10:8] [7:5] [4:2] [1:0]
funct3   imm    rs2    rs1   rd   opcode


### Educational Benefits

The core provides excellent visibility into processor operation through:
- **Real-time register outputs**: Current execution results appear immediately on output pins
- **Program counter visibility**: 5-bit PC value is observable on debug pins
- **Register address tracking**: Shows which register is currently being accessed
- **Branch decision feedback**: Indicates when branches are taken

## How to test

### Basic Setup

1. **Clock**: Connect a clock signal (1-10 MHz recommended for easy observation)
2. **Reset**: Pull rst_n low to reset, then high to begin operation
3. **Power**: Ensure ena is high (always high on Tiny Tapeout)

### Loading Instructions

PicoRISC-V uses a simple 2-cycle instruction loading protocol:

1. **First Cycle**: 
   - Set `ui` (LOAD_EN) = 1[1]
   - Set `ui[6:0]` to the lower 7 bits of your 16-bit instruction
   - Apply clock edge

2. **Second Cycle**:
   - Keep `ui` (LOAD_EN) = 1[1]
   - Set `uio[7:0]` to the upper 8 bits of your 16-bit instruction
   - Apply clock edge

3. **Execute**:
   - Set `ui` (LOAD_EN) = 0[1]
   - Apply clock edge to execute the instruction

### Example Test Sequence

**Load Immediate**: Load value 5 into register R1

Instruction: 0x0285 (LI R1, #5)
Cycle 1: ui = 0x85, uio = don't care
Cycle 2: ui = 0x82, uio = 0x02
Cycle 3: ui = 0x02, uio = don't care (execute)
Result: uo_out shows 0x05, uio_out shows R1 address


**Add Operation**: Add R1 + R1, store in R2

Instruction: 0x0089 (ADD R2, R1, R1)  
Cycle 1: ui = 0x89, uio = don't care
Cycle 2: ui = 0x80, uio = 0x00
Cycle 3: ui = 0x00, uio = don't care (execute)
Result: uo_out shows 0x0A (10), uio_out shows R2 address


**Branch Test**: Branch if R1 equals R2

Instruction: 0x008B (BEQ R1, R2, offset)
Result: Branch taken = 0 (since 5 ≠ 10), PC increments normally


### Monitoring Outputs

- **uo_out[7:0]**: Current register value or execution result
- **uio_out[2:0]**: Current register address being accessed (R0-R7)
- **uio_out[7:3]**: Program counter value (0-31)

### Educational Exercises

1. **Basic Arithmetic**: Test ADD, SUB operations with immediate values
2. **Logic Operations**: Verify AND, OR, XOR with different bit patterns  
3. **Conditional Branches**: Create simple loops using branch instructions
4. **Register Usage**: Observe how different registers store and output values
5. **Program Flow**: Track program counter progression through instruction sequences

## External hardware

**Minimal Setup**: No external hardware required - the core can be tested using:
- Tiny Tapeout demo board with DIP switches for input
- LEDs for output observation
- Logic analyzer or oscilloscope for detailed signal analysis

**Recommended Educational Setup**:
- **Input**: 8x DIP switches or push buttons for instruction loading
- **Output**: 8x LEDs to display register values and results  
- **Debug**: Additional LEDs or 7-segment display to show program counter
- **Clock**: Function generator or adjustable clock source (1-10 MHz)
- **Logic Analyzer**: For detailed instruction timing analysis

**Advanced Setup**:
- **Microcontroller Interface**: Arduino or Raspberry Pi to automate instruction loading and create educational demos
- **Serial Interface**: Connect to computer for programmatic testing and educational software
- **Breadboard Setup**: Wire up manual instruction entry system with switches and displays

The core is specifically designed to work with minimal external components, making it ideal for educational environments where students can manually input instructions and immediately observe the results, fostering a deep understanding of processor fundamentals.

[9](https://yeokhengmeng.com/2024/06/my-first-chip-with-tiny-tapeout-cvx/)
[10](https://www.reddit.com/r/RISCV/comments/1gr8h15/advice_needed_for_choosing_a_small_riscv_cpu_with/)
[11](https://github.com/MichaelBell/tinyQV/)
