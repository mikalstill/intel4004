from functools import partial

from intel4004 import registers


class UnknownOpcode(Exception):
    ...


class OpcodeCollision(Exception):
    ...


class OpcodeRegistry():
    def __init__(self):
        self.opcodes = {}

    def register(self, opcode, function):
        if opcode in self.opcodes:
            raise OpcodeCollision(
                f'opcode {opcode:02x} is already registered to '
                f'{self.opcodes[opcode]}')
        self.opcodes[opcode] = function

    def lookup(self, opcode):
        if opcode not in self.opcodes:
            raise UnknownOpcode(f'opcode {opcode:02x} is not registered')
        return self.opcodes[opcode]


class Intel4004():
    def __init__(self):
        # We have 16 four bit registers, as described on page 2-2 of the assembly
        # language manual.
        self.four_bit_registers = {}
        for i in range(16):
            name = f'{i}'
            self.four_bit_registers[name] = registers.FourBitRegister(name)

        # Those four bit registers can be paired into eight bit registers. Also
        # page 2-2.
        self.eight_bit_registers = {}
        for i in range(8):
            name = f'{i}P'
            self.eight_bit_registers[name] = registers.EightBitPhantomRegister(
                name,
                self.four_bit_registers[f'{i * 2}'],
                self.four_bit_registers[f'{i * 2 + 1}'])

        # Control registers, per page 2-3 of the assembly language manual.
        self.program_counter = registers.TwelveBitRegister('pc')
        self.accumulator = registers.FourBitRegister('acc')
        self.carry = registers.OneBitRegister('carry')
        self.data_pointer = registers.EightBitRegister('dp')

        # Stack. This is described on page 2-7 of the assembly language manual.
        # These three registers form a circular buffer.
        self.stack = registers.CircularBuffer(
            registers.TwelveBitRegister('stack-0'),
            registers.TwelveBitRegister('stack-1'),
            registers.TwelveBitRegister('stack-2'))

        # Actually a pin, but we model it as a one bit register
        self.test_pin = registers.OneBitRegister('test')

        # We have 4,096 eight bit bytes of ROM and RAM respectively
        self.rom = [0] * 4096

        # Dispatcher for opcodes
        self._dispatch_map = OpcodeRegistry()
        self._dispatch_map.register(0x00, self.opcode_noop)
        self._dispatch_map.register(0xF0, self.opcode_clb)
        self._dispatch_map.register(0xF1, self.opcode_clc)
        self._dispatch_map.register(0xF2, self.opcode_iac)
        self._dispatch_map.register(0xF8, self.opcode_dac)

        # Per 4-bit register instructions
        for i in range(16):
            self._dispatch_map.register(
                0x60 + i, partial(self.opcode_inc, f'{i}'))
            self._dispatch_map.register(
                0x80 + i, partial(self.opcode_add, f'{i}'))
            self._dispatch_map.register(
                0x90 + i, partial(self.opcode_sub, f'{i}'))
            self._dispatch_map.register(
                0xA0 + i, partial(self.opcode_ld, f'{i}'))
            self._dispatch_map.register(
                0xB0 + i, partial(self.opcode_xch, f'{i}'))

        # Per 8-bit register instructions
        for i in range(8):
            register = i << 1
            self._dispatch_map.register(
                0x20 | register, partial(self.opcode_fim, f'{i}P'))

            self._dispatch_map.register(
                0x30 | register | 0x01, partial(self.opcode_jin, f'{i}P'))

        # Immediate value instructions
        for i in range(16):
            self._dispatch_map.register(0xC0 + i, partial(self.opcode_bbl, i))
            self._dispatch_map.register(0xD0 + i, partial(self.opcode_ldm, i))

        # Immediate value 12 bit argument instructions. The next byte is read
        # by the opcode implementation below.
        for i in range(2**4 - 1):
            self._dispatch_map.register(0x10 + i, partial(self.opcode_jcn, i))
            self._dispatch_map.register(0x40 + i, partial(self.opcode_jun, i))
            self._dispatch_map.register(0x50 + i, partial(self.opcode_jms, i))

    def set_rom(self, address, rom):
        for i in range(len(rom)):
            self.rom[address + i] = rom[i]

    def step(self):
        opcode = self.rom[self.program_counter.get()]
        self.program_counter.increment()
        self._dispatch_map.lookup(opcode)()

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

    def opcode_jin(self, eight_bit_register):
        # 0x3_ / JIN / Jump indirect, where the relative address to jump to is
        # in the specified 8-bit register. The top four bits of the original
        # program counter are retained.
        address = self.program_counter.get() & 0x0F00
        address = address | self.eight_bit_registers[eight_bit_register].get()
        self.program_counter.set(address)

    def opcode_jms(self, top_four_bits_of_address):
        # 0x45_ / JMS / Jump to 12 bit address with four bits from the opcode
        # and the other four bits from the object code stream. Put ROM address
        # after this instruction onto the stack before jumping.
        new_address = top_four_bits_of_address << 8
        new_address += self.rom[self.program_counter.get()]
        return_address = self.program_counter.get() + 1
        self.stack.push(return_address)
        self.program_counter.set(new_address)

    def opcode_inc(self, four_bit_register):
        # 0x6_ / INC / Increment register, without changing carry.
        try:
            self.four_bit_registers[four_bit_register].increment()
        except registers.ValueOutOfBounds:
            self.four_bit_registers[four_bit_register].set(0)

    def opcode_jun(self, top_four_bits_of_address):
        # 0x4_ / JUN / Jump to 12 bit address with four bits from the opcode
        # and the other four bits from the object code stream
        address = top_four_bits_of_address << 8
        address += self.rom[self.program_counter.get()]
        self.program_counter.set(address)

    def opcode_add(self, four_bit_register):
        # 0x8_ / ADD / Add register value to accumulator
        value = self.accumulator.get()
        value += self.carry.get()
        value += self.four_bit_registers[four_bit_register].get()

        if value > registers.MAX_FOUR_BIT_VALUE:
            self.carry.set(1)
            value -= 2**4

        self.accumulator.set(value)

    def opcode_sub(self, four_bit_register):
        # 0x9_ / SUB / Subtract register value from accumulator
        value = self.accumulator.get()

        register = self.four_bit_registers[four_bit_register].get_inverted()
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

    def opcode_ld(self, four_bit_register):
        # 0xA_ / LD / Load register value into accumulator
        self.accumulator.set(self.four_bit_registers[four_bit_register].get())

    def opcode_xch(self, four_bit_register):
        # 0xB_ / XCH / Exchange accumulator with register
        r = self.four_bit_registers[four_bit_register].get()
        self.four_bit_registers[four_bit_register].set(self.accumulator.get())
        self.accumulator.set(r)

    def opcode_bbl(self, value):
        # 0x6_ / BBL / Branch back (return from subroutine) and load immediate
        # value into accumulator.
        self.program_counter.set(self.stack.pop())
        self.accumulator.set(value)

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
