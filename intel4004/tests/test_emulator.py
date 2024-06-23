import testtools

from intel4004 import emulator
from intel4004 import registers


class EmulatorTests(testtools.TestCase):
    def test_initialization(self):
        em = emulator.Intel4004()

        # Check number of index registers and their initial state
        self.assertEqual(16, len(em.four_bit_registers))
        self.assertEqual(8, len(em.eight_bit_registers))
        for i in range(16):
            self.assertEqual(0, em.four_bit_registers[f'{i}'].get())
        for i in range(8):
            self.assertEqual(0, em.eight_bit_registers[f'{i}P'].get())

    def test_register_operation(self):
        em = emulator.Intel4004()

        em.four_bit_registers['0'].set(12)
        self.assertEqual(12, em.four_bit_registers['0'].get())
        em.four_bit_registers['8'].set(12)
        self.assertEqual(12, em.four_bit_registers['8'].get())

        em.eight_bit_registers['1P'].set(42)
        self.assertEqual(2, em.four_bit_registers['2'].get())
        self.assertEqual(10, em.four_bit_registers['3'].get())
        self.assertEqual(42, em.eight_bit_registers['1P'].get())

    def test_control_state(self):
        em = emulator.Intel4004()
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(0, em.program_counter.get())


class OpcodeTests(testtools.TestCase):
    ###########################################################################
    # NOP (noop) is documented on page 3-48 of the assembly language manual.
    def test_noop(self):
        em = emulator.Intel4004()
        em.set_rom(0, [0x00, 0x00, 0x00])
        self.assertEqual(0, em.program_counter.get())
        em.step()
        self.assertEqual(1, em.program_counter.get())

    ###########################################################################
    # Possible JCN conditions from MCS-4 users manual page 133. These are shown
    # on page 136 as additional instructions, although they aren't really.
    #     JTZ Jump on test zero
    #     JTN Jump on test not zero
    #     JTO Jump on test one
    #     JCZ Jump on carry/line zero
    #     JNC Jump on no carry (i.e. = 0)
    #     JCO Jump on carry/link one
    #     JOC Jump on carry
    #     JAZ Jump on accumulator zero
    #     JNZ Jump on accumulator not zero
    #     JAN Jump on accumulator not zero
    #
    # Page 134 of the MCS-4 users manual states that operator mnemonics are
    # defined in the assembler as integer constants. This means that different
    # assemblers _might_ use different mnemonics for these operations.
    #
    # For example, http://e4004.szyc.org/asm.html appears to use these mnemonics:
    #     szyc     MCS-4    Hex
    #     NC       ...      0
	#     TZ       JTZ      1
	#     T0       ...      1
	#     TN       JTN      9
	#     T1       JTO      9
	#     CN       JNC      2   (intel docs say this is A)
	#     C1       JOC      2   (intel docs say this is A)
	#     CZ       JCZ      A   (intel docs say this is 2)
	#     C0       JCO      A   (intel docs say this is 2)
	#     AZ       JAZ      4
	#     A0       ...      4
	#     AN       JAN      C
	#     NZA      JNZ      C
    #
    # That is, I think there is a bug in the szyc.org assembler.

    def test_jcn_jtz_test_true(self):
        em = emulator.Intel4004()
        em.test_pin.set(0)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x11, 0x23])
        em.step()
        self.assertEqual(0x0B23, em.program_counter.get())

    def test_jcn_jtz_test_false(self):
        em = emulator.Intel4004()
        em.test_pin.set(1)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x11, 0x23])
        em.step()
        self.assertEqual(0x0B14, em.program_counter.get())

    def test_jcn_jtn_jto_test_true(self):
        em = emulator.Intel4004()
        em.test_pin.set(1)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x19, 0x23])
        em.step()
        self.assertEqual(0x0B23, em.program_counter.get())

    def test_jcn_jtn_jto_test_false(self):
        em = emulator.Intel4004()
        em.test_pin.set(0)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x19, 0x23])
        em.step()
        self.assertEqual(0x0B14, em.program_counter.get())

    def test_jcn_jnc_joc_test_true(self):
        em = emulator.Intel4004()
        em.carry.set(0)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x1A, 0x23])
        em.step()
        self.assertEqual(0x0B23, em.program_counter.get())

    def test_jcn_jnc_joc_test_false(self):
        em = emulator.Intel4004()
        em.carry.set(1)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x1A, 0x23])
        em.step()
        self.assertEqual(0x0B14, em.program_counter.get())

    def test_jcn_jcz_jco_test_true(self):
        em = emulator.Intel4004()
        em.carry.set(1)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x12, 0x23])
        em.step()
        self.assertEqual(0x0B23, em.program_counter.get())

    def test_jcn_jcz_jco_test_false(self):
        em = emulator.Intel4004()
        em.carry.set(0)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x12, 0x23])
        em.step()
        self.assertEqual(0x0B14, em.program_counter.get())

    def test_jcn_jaz_test_true(self):
        em = emulator.Intel4004()
        em.accumulator.set(0)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x14, 0x23])
        em.step()
        self.assertEqual(0x0B23, em.program_counter.get())

    def test_jcn_jaz_test_false(self):
        em = emulator.Intel4004()
        em.accumulator.set(1)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x14, 0x23])
        em.step()
        self.assertEqual(0x0B14, em.program_counter.get())

    def test_jcn_jan_jnz_test_true(self):
        em = emulator.Intel4004()
        em.accumulator.set(1)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x1C, 0x23])
        em.step()
        self.assertEqual(0x0B23, em.program_counter.get())

    def test_jcn_jan_jnz_test_false(self):
        em = emulator.Intel4004()
        em.accumulator.set(0)
        em.program_counter.set(0x0B12)
        em.set_rom(0x0B12, [0x1C, 0x23])
        em.step()
        self.assertEqual(0x0B14, em.program_counter.get())

    # JCN also has special maths if the jump instruction bytes are at the end
    # of a ROM page.
    def test_jcn_jan_jnz_test_true_end_of_rom(self):
        em = emulator.Intel4004()
        em.accumulator.set(1)
        em.program_counter.set(0x00FE)
        em.set_rom(0xFE, [0x1C, 0x06])
        em.step()
        self.assertEqual(0x0106, em.program_counter.get())

    ###########################################################################
    # FIM (fetch immediate) is documented on page 3-36 of the assembly language
    # manual. This instruction loads a _byte_ into one of the 8-bit pseudo
    # registers.
    def test_fim(self):
        em = emulator.Intel4004()
        em.set_rom(0x00, [0x24, 0x12])
        em.step()
        self.assertEqual(0x02, em.program_counter.get())
        self.assertEqual(0x12, em.eight_bit_registers['2P'].get())

    ###########################################################################
    # JIN (jump indirect) is documented on page 3-40 of the assembly language
    # manual.
    def test_jin(self):
        em = emulator.Intel4004()
        em.eight_bit_registers['2P'].set(0x78)
        em.set_rom(0x0100, [0x35, 0x12])
        em.program_counter.set(0x0100)
        em.step()
        self.assertEqual(0x0178, em.program_counter.get())

    ###########################################################################
    # INC (increment register) is documented on page 3-17 of the assembly language
    # manual.
    def test_jin(self):
        em = emulator.Intel4004()
        em.four_bit_registers['3'].set(6)
        em.four_bit_registers['8'].set(15)
        em.four_bit_registers['9'].set(15)
        em.set_rom(0x00, [0x63, 0x68, 0x69])

        em.step()
        self.assertEqual(7, em.four_bit_registers['3'].get())
        self.assertEqual(0, em.carry.get())

        em.step()
        self.assertEqual(0, em.four_bit_registers['8'].get())
        self.assertEqual(0, em.carry.get())

        em.carry.set(1)
        em.step()
        self.assertEqual(0, em.four_bit_registers['9'].get())
        self.assertEqual(1, em.carry.get())

    ###########################################################################
    # JUN (jump unconditionally) is documented on page 3-48 of the assembly
    # language manual. This jump can be to another memory page.
    def test_jun(self):
        em = emulator.Intel4004()
        em.program_counter.set(0x00FE)
        em.set_rom(0xFE, [0x41, 0x23])
        em.step()
        self.assertEqual(0x0123, em.program_counter.get())

    ###########################################################################
    # ADD (add register value to accumulator with carry) is documented on page
    # 3-21 of the assembly language manual.
    def test_add_no_incoming_carry(self):
        em = emulator.Intel4004()
        em.accumulator.set(0x06)
        em.carry.set(0)
        em.four_bit_registers['14'].set(0x09)
        em.set_rom(0x00, [0x8E])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0x0F, em.accumulator.get())
        self.assertEqual(0, em.carry.get())

    def test_add_incoming_carry(self):
        em = emulator.Intel4004()
        em.accumulator.set(0x06)
        em.carry.set(1)
        em.four_bit_registers['14'].set(0x09)
        em.set_rom(0x00, [0x8E])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0x00, em.accumulator.get())
        self.assertEqual(1, em.carry.get())

    ###########################################################################
    # SUB (subtract from accumulator) is documented on page 3-22 of the assembly
    # language manual. Note that the right way to implement these operations is
    # with 1s complement maths, as documented in the manual.
    def test_sub_no_incoming_carry(self):
        em = emulator.Intel4004()
        em.accumulator.set(0b0110)
        em.carry.set(0)
        em.four_bit_registers['10'].set(0b0010)
        em.set_rom(0x00, [0x9A])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0b0100, em.accumulator.get())
        self.assertEqual(1, em.carry.get())

    def test_sub_incoming_carry(self):
        em = emulator.Intel4004()
        em.accumulator.set(0b0110)
        em.carry.set(1)
        em.four_bit_registers['10'].set(0b0010)
        em.set_rom(0x00, [0x9A])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0b0011, em.accumulator.get())
        self.assertEqual(1, em.carry.get())

    def test_sub_no_outgoing_carry(self):
        _source = ('  ldm 10\n'
                   '  xch r1\n'
                   '  ldm 6\n'
                   '  sub r1')
        _compiled = [0xDA, 0xB1, 0xD6, 0x91]

        em = emulator.Intel4004()
        em.accumulator.set(0x06)
        em.carry.set(0)
        em.four_bit_registers['1'].set(0x0A)
        em.set_rom(0x00, [0x91])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0x0C, em.accumulator.get())
        self.assertEqual(0, em.carry.get())

    ###########################################################################
    # LD (load accumulator) is documented on page 3-24 of the assembly language
    # manual.
    def test_ld(self):
        em = emulator.Intel4004()
        em.four_bit_registers['1'].set(0b1010)
        em.set_rom(0x00, [0b10100001])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0b1010, em.accumulator.get())

    ###########################################################################
    # XCH (exchange register and accumulator) is documented on page 3-25 of the
    # assembly language manual.
    def test_xch(self):
        em = emulator.Intel4004()
        em.accumulator.set(0b0101)
        em.four_bit_registers['1'].set(0b1010)
        em.set_rom(0x00, [0b10110001])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0b1010, em.accumulator.get())
        self.assertEqual(0b0101, em.four_bit_registers['1'].get())
        self.assertEqual(0, em.carry.get())

    ###########################################################################
    # LDM (load accumulator immediate) is documented on page 3-37 of the
    # assembly language manual.
    def test_ldm(self):
        em = emulator.Intel4004()
        em.set_rom(0x00, [0b11010001])
        em.step()
        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0b0001, em.accumulator.get())

    ###########################################################################
    # CLB (clear both) is documented on page 3-27 of the assembly language
    # manual.
    def test_clb(self):
        em = emulator.Intel4004()
        em.carry.set(1)
        em.accumulator.set(0b0101)
        em.set_rom(0x00, [0b11110000])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(0, em.carry.get())

    ###########################################################################
    # CLC (clear carry) is documented on page 3-27 of the assembly language
    # manual.
    def test_clc(self):
        em = emulator.Intel4004()
        em.carry.set(1)
        em.accumulator.set(0b0101)
        em.set_rom(0x00, [0b11110001])
        em.step()

        self.assertEqual(0x01, em.program_counter.get())
        self.assertEqual(0b0101, em.accumulator.get())
        self.assertEqual(0, em.carry.get())

    ###########################################################################
    # IAC (increment accumulator) is documented on page 3-28 of the assembly
    # language manual.
    def test_iac(self):
        ...

    ###########################################################################
    # DAC (decrement accumulator) is documented on page 3-32 of the assembly
    # language manual.
    def test_dac_carry(self):
        em = emulator.Intel4004()
        em.accumulator.set(9)
        em.set_rom(0x00, [0xF8])
        em.step()
        self.assertEqual(8, em.accumulator.get())
        self.assertEqual(1, em.carry.get())

    def test_dac_no_carry(self):
        em = emulator.Intel4004()
        em.accumulator.set(0)
        em.set_rom(0x00, [0xF8])
        em.step()
        self.assertEqual(0xE, em.accumulator.get())
        self.assertEqual(0, em.carry.get())


class ProgramTests(testtools.TestCase):
    def test_program_one(self):
        # https://github.com/CodeAbbey/intel4004-emu/wiki/First-instructions
        source = ('  ldm 5\n'
                  '  xch r2\n')
        compiled = [0xD5, 0xB2]

        em = emulator.Intel4004()
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(0, em.four_bit_registers['2'].get())
        self.assertEqual(0, em.program_counter.get())

        em.set_rom(0, compiled)
        em.step()  # LDM 5
        self.assertEqual(5, em.accumulator.get())
        self.assertEqual(0, em.four_bit_registers['2'].get())
        self.assertEqual(1, em.program_counter.get())
        em.step()  # XCH R2
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(5, em.four_bit_registers['2'].get())
        self.assertEqual(2, em.program_counter.get())

    def test_program_two(self):
        # https://github.com/CodeAbbey/intel4004-emu/wiki/Jump-instructions
        source = ('  ldm 5\n'
                  '  xch r0\n'
                  '  jun skip_few\n'
                  '  ldm 6\n'
                  '  xch r1\n'
                  'skip_few:\n'
                  '  ldm 7\n'
                  '  xch r2\n')
        compiled = [0xD5, 0xB0, 0x40, 0x06, 0xD6, 0xB1, 0xD7, 0xB2]

        em = emulator.Intel4004()
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(0, em.four_bit_registers['0'].get())
        self.assertEqual(0, em.four_bit_registers['2'].get())
        self.assertEqual(0, em.program_counter.get())

        em.set_rom(0, compiled)
        em.step()  # LDM 5
        self.assertEqual(5, em.accumulator.get())
        self.assertEqual(0, em.four_bit_registers['0'].get())
        self.assertEqual(0, em.four_bit_registers['2'].get())
        self.assertEqual(1, em.program_counter.get())
        em.step()  # XCH R0
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(5, em.four_bit_registers['0'].get())
        self.assertEqual(0, em.four_bit_registers['2'].get())
        self.assertEqual(2, em.program_counter.get())
        em.step()  # JUN skip_few
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(5, em.four_bit_registers['0'].get())
        self.assertEqual(0, em.four_bit_registers['2'].get())
        self.assertEqual(6, em.program_counter.get())
        em.step()  # LDM 7
        self.assertEqual(7, em.accumulator.get())
        self.assertEqual(5, em.four_bit_registers['0'].get())
        self.assertEqual(0, em.four_bit_registers['2'].get())
        self.assertEqual(7, em.program_counter.get())
        em.step()  # XCH R2
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(5, em.four_bit_registers['0'].get())
        self.assertEqual(7, em.four_bit_registers['2'].get())
        self.assertEqual(8, em.program_counter.get())

    def test_program_three(self):
        # https://www.codeabbey.com/index/wiki/intel-4004-emulator
        source = ('  iac\n'
                  '  xch r1\n'
                  '  nop\n')
        compiled = [0xF2, 0xB1, 0x00]

        em = emulator.Intel4004()
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(0, em.four_bit_registers['1'].get())
        self.assertEqual(0, em.program_counter.get())

        em.set_rom(0, compiled)
        em.step()  # IAC
        self.assertEqual(1, em.accumulator.get())
        self.assertEqual(0, em.four_bit_registers['1'].get())
        self.assertEqual(1, em.program_counter.get())
        em.step()  # XCH R1
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(1, em.four_bit_registers['1'].get())
        self.assertEqual(2, em.program_counter.get())
        em.step()  # NOP
        self.assertEqual(0, em.accumulator.get())
        self.assertEqual(1, em.four_bit_registers['1'].get())
        self.assertEqual(3, em.program_counter.get())

    def test_program_four(self):
        # https://github.com/CodeAbbey/intel4004-emu/wiki/Jump-instructions
        source = ('  ldm 4     ; load 4 to r0 - it will be counter\n'
                  '  xch r0\n'
                  '\n'
                  '  one_more:\n'
                  '\n'
                  '  clc       ; add r0 to r1 which will hold the total\n'
                  '  ld r1\n'
                  '  add r0\n'
                  '  xch r1\n'
                  '\n'
                  '  ld r0     ; decrement r0 via acc\n'
                  '  dac\n'
                  '  xch r0\n'
                  '  jcn c1 one_more ; and jump if there was no borrow\n')
        compiled = [0xD4, 0xB0, 0xF1, 0xA1, 0x80, 0xB1, 0xA0, 0xF8, 0xB0,
                    0x12, 0x02]

        em = emulator.Intel4004()
        em.set_rom(0, compiled)

        # A different approach to the test here. Let's run the program until
        # we fall off the end (there is no halt instruction) and then test
        # we get the right result.
        while em.program_counter.get() < len(compiled):
            em.step()

        self.assertEqual(4 + 3 + 2 + 1, em.four_bit_registers['1'].get())
