import testtools

from intel4004 import registers


class BaseTestsMixin():
    def test_name(self):
        self.assertRaises(registers.NameInvalid, self.reg_class, 0)

    def test_value_minimum(self):
        self.assertRaises(
            registers.ValueOutOfBounds, self.reg_class, '0', -1)

    def test_value_maximum(self):
        self.assertRaises(
            registers.ValueOutOfBounds, self.reg_class, '0', self.too_large_value)

    def test_value_invalid(self):
        self.assertRaises(
            registers.ValueInvalid, self.reg_class, '0', 'banana')

    def test_value_increment(self):
        r = self.reg_class('0')
        self.assertEqual(0, r.get())
        r.increment()
        self.assertEqual(1, r.get())

    def test_value_decrement(self):
        r = self.reg_class('0', 1)
        self.assertEqual(1, r.get())
        r.decrement()
        self.assertEqual(0, r.get())


class OneBitRegisterTests(testtools.TestCase, BaseTestsMixin):
    def setUp(self):
        super().setUp()
        self.reg_class = registers.OneBitRegister
        self.too_large_value = 2**1

    def test_value_lifecycle(self):
        r = registers.OneBitRegister('0')
        self.assertEqual('0', r.name)
        self.assertEqual(0, r.get())
        r.set(1)
        self.assertEqual(1, r.get())
        self.assertEqual('One bit register 0 with value 1', repr(r))

    def test_get_inverted(self):
        r = registers.OneBitRegister('carry')
        r.set(0b0)
        self.assertEqual(0b1, r.get_inverted())
        r.set(0b1)
        self.assertEqual(0b0, r.get_inverted())


class FourBitRegisterTests(testtools.TestCase, BaseTestsMixin):
    def setUp(self):
        super().setUp()
        self.reg_class = registers.FourBitRegister
        self.too_large_value = 2**4

    def test_value_lifecycle(self):
        r = registers.FourBitRegister('0')
        self.assertEqual('0', r.name)
        self.assertEqual(0, r.get())
        r.set(12)
        self.assertEqual(12, r.get())
        self.assertEqual('Four bit register 0 with value 12', repr(r))

    def test_get_inverted(self):
        r = registers.FourBitRegister('reg')
        r.set(0b0000)
        inverted = r.get_inverted()
        self.assertEqual(0b1111, inverted,
                         f'0000 not inverted correctly, got {inverted:04b}')

        r.set(0b1010)
        inverted = r.get_inverted()
        self.assertEqual(0b0101, inverted,
                         f'1010 not inverted correctly, got {inverted:04b}')


class EightBitPhantomRegisterTests(testtools.TestCase, BaseTestsMixin):
    def setUp(self):
        super().setUp()
        self.reg_class = registers.EightBitRegister
        self.too_large_value = 2**8

    def test_value_lifecycle(self):
        h = registers.EightBitRegister('0')
        l = registers.EightBitRegister('1')
        r = registers.EightBitPhantomRegister('0P', h, l)

        self.assertEqual('0P', r.name)
        self.assertEqual(0, r.get())
        r.set(42)
        self.assertEqual(2, r.high_reg.get())
        self.assertEqual(10, r.low_reg.get())
        self.assertEqual(42, r.get())
        self.assertEqual(
            'Eight bit phantom register 0P with value 42', repr(r))

    def test_get_inverted(self):
        h = registers.EightBitRegister('0')
        l = registers.EightBitRegister('1')
        r = registers.EightBitPhantomRegister('reg', h, l)
        r.set(0b00000000)
        inverted = r.get_inverted()
        self.assertEqual(0b11111111, inverted,
                         f'00000000 not inverted correctly, got {inverted:04b}')

        r.set(0b10101010)
        inverted = r.get_inverted()
        self.assertEqual(0b01010101, inverted,
                         f'10101010 not inverted correctly, got {inverted:04b}')


class EightBitRegisterTests(testtools.TestCase, BaseTestsMixin):
    def setUp(self):
        super().setUp()
        self.reg_class = registers.EightBitRegister
        self.too_large_value = 2**8

    def test_value_lifecycle(self):
        r = registers.EightBitRegister('DP')
        self.assertEqual('DP', r.name)
        self.assertEqual(0, r.get())
        r.set(12)
        self.assertEqual(12, r.get())
        self.assertEqual('Eight bit register DP with value 12', repr(r))

    def test_get_inverted(self):
        r = registers.EightBitRegister('reg')
        r.set(0b00000000)
        inverted = r.get_inverted()
        self.assertEqual(0b11111111, inverted,
                         f'00000000 not inverted correctly, got {inverted:04b}')

        r.set(0b10101010)
        inverted = r.get_inverted()
        self.assertEqual(0b01010101, inverted,
                         f'10101010 not inverted correctly, got {inverted:04b}')


class TwelveBitRegisterTests(testtools.TestCase, BaseTestsMixin):
    def setUp(self):
        super().setUp()
        self.reg_class = registers.TwelveBitRegister
        self.too_large_value = 2**12

    def test_value_lifecycle(self):
        r = registers.TwelveBitRegister('PC')
        self.assertEqual('PC', r.name)
        self.assertEqual(0, r.get())
        r.set(12)
        self.assertEqual(12, r.get())
        self.assertEqual('Twelve bit register PC with value 12', repr(r))

    def test_get_inverted(self):
        r = registers.TwelveBitRegister('reg')
        r.set(0b000000000000)
        inverted = r.get_inverted()
        self.assertEqual(
            0b111111111111, inverted,
            f'000000000000 not inverted correctly, got {inverted:04b}')

        r.set(0b101010101010)
        inverted = r.get_inverted()
        self.assertEqual(
            0b010101010101, inverted,
            f'101010101010 not inverted correctly, got {inverted:04b}')


class CircularBufferTests(testtools.TestCase):
    def test_circular_buffer(self):
        cb = registers.CircularBuffer(
            registers.TwelveBitRegister('stack-0'),
            registers.TwelveBitRegister('stack-1'),
            registers.TwelveBitRegister('stack-2')
        )

        cb.push(1)
        self.assertEqual(1, cb.registers[0].get())
        cb.push(2)
        self.assertEqual(2, cb.registers[1].get())
        cb.push(3)
        self.assertEqual(3, cb.registers[2].get())
        cb.push(4)
        self.assertEqual(4, cb.registers[0].get())

        self.assertEqual(4, cb.pop())
        self.assertEqual(3, cb.pop())
        self.assertEqual(2, cb.pop())
