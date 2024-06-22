from functools import partial

from intel4004 import registers


class UnknownOpcode(Exception):
    ...


class Intel4004():
    def __init__(self):
        # We have 16 four bit registers
        self.four_bit_registers = {}
        for i in range(16):
            name = f'{i}'
            self.four_bit_registers[name] = registers.FourBitRegister(name)

        # Those four bit registers can be paired into eight bit registers
        self.eight_bit_registers = {}
        for i in range(8):
            name = f'{i}P'
            self.eight_bit_registers[name] = registers.EightBitPhantomRegister(
                name,
                self.four_bit_registers[f'{i * 2}'],
                self.four_bit_registers[f'{i * 2 + 1}'])

        # Control registers
        self.program_counter = registers.TwelveBitRegister('pc')
        self.accumulator = registers.FourBitRegister('acc')
        self.carry = registers.OneBitRegister('carry')
        self.data_pointer = registers.EightBitRegister('dp')
        self.return_stack = [
            registers.TwelveBitRegister('stack-0'),
            registers.TwelveBitRegister('stack-1'),
            registers.TwelveBitRegister('stack-2')
        ]

        # Actually a pin, but we model it as a one bit register
        self.test_pin = registers.OneBitRegister('test')

        # We have 4,096 eight bit bytes of ROM and RAM respectively
        self.rom = [0] * 4096

        # Dispatcher for opcodes
        self._dispatch_map = {
            0x00: self.opcode_noop,
            0xF0: self.opcode_clb,
            0xF1: self.opcode_clc,
            0xF2: self.opcode_iac,
            0xF8: self.opcode_dac,
        }

        # Per 4-bit register instructions
        for i in range(16):
            self._dispatch_map[0x80 + i] = partial(self.opcode_add, f'{i}')
            self._dispatch_map[0x90 + i] = partial(self.opcode_sub, f'{i}')
            self._dispatch_map[0xA0 + i] = partial(self.opcode_ld, f'{i}')
            self._dispatch_map[0xB0 + i] = partial(self.opcode_xch, f'{i}')

        # Per 8-bit register instructions
        for i in range(8):
            register = i << 1
            self._dispatch_map[0x20 | register] = \
                partial(self.opcode_fim, f'{i}P')

        # Immediate value instructions
        for i in range(16):
            self._dispatch_map[0xD0 + i] = partial(self.opcode_ldm, i)

        # Immediate value 12 bit argument instructions. The next byte is read
        # by the opcode implementation below.
        for i in range(2**4 - 1):
            self._dispatch_map[0x10 + i] = partial(self.opcode_jcn, i)
            self._dispatch_map[0x40 + i] = partial(self.opcode_jun, i)

    def set_rom(self, address, rom):
        for i in range(len(rom)):
            self.rom[address + i] = rom[i]

    def step(self):
        opcode = self.rom[self.program_counter.get()]
        if opcode not in self._dispatch_map:
            raise UnknownOpcode(f'opcode 0x{opcode:02X} is unknown')

        self.program_counter.increment()
        self._dispatch_map[opcode]()

    def dump(self, opcode):
        print(f'--> Executed opcode {opcode:02X}')
        print()

        print(f'    Program counter: {self.program_counter.get():03X}')
        print(f'    Accumulator: {self.program_counter.get():01X}')
        print(f'          Carry: {self.carry.get():01X}')
        print(f'    Data pointer: {self.data_pointer.get():02X}')
        print(f'    Stack 0: {self.return_stack[0].get():03X}')
        print(f'    Stack 1: {self.return_stack[1].get():03X}')
        print(f'    Stack 2: {self.return_stack[2].get():03X}')
        print()
        for i in range(8):
            print(f'    Registers {i * 2:02}, and {i * 2 + 1:02}: '
                  f'{self.four_bit_registers[str(i * 2)].get():01X} '
                  f'{self.four_bit_registers[str(i * 2 + 1)].get():01X}')
        print()

    # Opcodes, ordered by numeric object code value
    def opcode_noop(self):
        # 0x00 / NOP / Noop
        # Assembly language programming manual page 3-48 (PDF page 77).
        ...

    def opcode_jcn(self, condition):
        # 0x10 / JCN / Jump conditional
        # Assembly language programming manual page 3-41 (PDF page 70).
        possible_address = self.rom[self.program_counter.get()]
        self.program_counter.increment()
        result = False

        # Ok, this is a little ugly... The top three bits are conditions, the
        # bottom (right most) bit is an inversion.
        if condition & 0x01:
            result = self.test_pin.get() == 0
        if condition & 0x02:
            result = self.carry.get() == 1
        if condition & 0x04:
            result = self.accumulator.get() == 0
        if condition & 0x08:
            result = not result

        if result:
            # If the result is true, we replace the lower 8 bits of the PC
            # with the possible address.
            pc = self.program_counter.get() & 0x0F00
            pc += possible_address

            # Additionally, if the program counter was at the end of a page,
            # then we increment the highest four bits of the program counter
            # too. However, we get this for free because we increment instead
            # simply doing a bit swap.

            self.program_counter.set(pc)

    def opcode_fim(self, eight_bit_register):
        # 0x2_ / FIM / Load 8-bit register immediate, where the value to load
        # is the next byte in ROM.
        value = self.rom[self.program_counter.get()]
        self.eight_bit_registers[eight_bit_register].set(value)
        self.program_counter.increment()

    def opcode_jun(self, top_four_bits_of_address):
        # 0x4_ / JUN / Jump to 12 bit address with four bits from the opcode
        # and the other four bits from the object code stream
        address = top_four_bits_of_address << 8
        address += self.rom[self.program_counter.get()]
        self.program_counter.set(address)

    def opcode_add(self, register_name):
        # 0x8_ / ADD / Add register value to accumulator
        value = self.accumulator.get()
        value += self.carry.get()
        value += self.four_bit_registers[register_name].get()

        if value > registers.MAX_FOUR_BIT_VALUE:
            self.carry.set(1)
            value -= 2**4

        self.accumulator.set(value)

    def opcode_sub(self, register_name):
        # 0x9_ / SUB / Subtract register value from accumulator
        value = self.accumulator.get()

        register = self.four_bit_registers[register_name].get_inverted()
        value += register

        carry = self.carry.get_inverted()
        value += carry

        # Handle overflow
        if value & 0b00010000 == 0:
            self.carry.set(0)
        else:
            self.carry.set(1)
            value -= 0b00010000
        self.accumulator.set(value)

    def opcode_ld(self, register_name):
        # 0xA_ / LD / Load register value into accumulator
        self.accumulator.set(self.four_bit_registers[register_name].get())

    def opcode_xch(self, register_name):
        # 0xB_ / XCH / Exchange accumulator with register
        r = self.four_bit_registers[register_name].get()
        self.four_bit_registers[register_name].set(self.accumulator.get())
        self.accumulator.set(r)

    def opcode_ldm(self, value):
        # 0xD_ / LDM / Load immediate
        self.accumulator.set(value)

    def opcode_clb(self):
        # OxF0 / CLB / Clear both
        self.carry.set(0)
        self.accumulator.set(0)

    def opcode_clc(self):
        # OxF1 / CLC / Clear carry
        self.carry.set(0)

    def opcode_iac(self):
        # 0xF2 / IAC / Increment accumulator
        self.accumulator.increment()

    def opcode_dac(self):
        # 0xF8 / DAC / Decrement accumulator
        acc = self.accumulator.get()
        acc -= 1
        if acc < 0:
            # Indicates a wrap around
            self.carry.set(0)
            self.accumulator.set(0xE)
        else:
            self.carry.set(1)
            self.accumulator.set(acc)
