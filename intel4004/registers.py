# MCS-4 assembly reference manual, page 11

MAX_ONE_BIT_VALUE = (2**1) - 1
MAX_FOUR_BIT_VALUE = (2**4) - 1
MAX_EIGHT_BIT_VALUE = (2**8) - 1
MAX_TWELVE_BIT_VALUE = (2**12) - 1


class NameInvalid(ValueError):
    ...


class ValueOutOfBounds(ValueError):
    ...


class ValueInvalid(ValueError):
    ...


class Register():
    def __init__(self, name, max_value):
        if type(name) != str:
            raise NameInvalid(name)
        self.name = name
        self.max_value = max_value

    def increment(self):
        self.set(self.get() + 1)

    def decrement(self):
        self.set(self.get() - 1)

    def set(self, value):
        if type(value) != int:
            raise ValueInvalid(value)

        if value < 0:
            raise ValueOutOfBounds(value)
        if value > self.max_value:
            raise ValueOutOfBounds(value)

        self.value = value

    def get(self):
        return self.value

    def get_inverted(self):
        value = self.get()
        out = 0
        for pow in range(0, self.num_bits):
            if not value & 2**pow:
                out += 2**pow
        return out


# Intel4004 has one one bit register.
class OneBitRegister(Register):
    num_bits = 1

    def __init__(self, name, value=0):
        super().__init__(name, MAX_ONE_BIT_VALUE)
        self.set(value)

    def __repr__(self):
        return f'One bit register {self.name} with value {self.get()}'


# Intel4004 has 16 four bit registers.
class FourBitRegister(Register):
    num_bits = 4

    def __init__(self, name, value=0):
        super().__init__(name, MAX_FOUR_BIT_VALUE)
        self.set(value)

    def __repr__(self):
        return f'Four bit register {self.name} with value {self.get()}'


# Intel4004 can use the four bit registers as eight eight bit registers.
class EightBitPhantomRegister(Register):
    num_bits = 8

    def __init__(self, name, high_reg, low_reg):
        super().__init__(name, MAX_EIGHT_BIT_VALUE)
        self.high_reg = high_reg
        self.low_reg = low_reg

    def __repr__(self):
        return f'Eight bit phantom register {self.name} with value {self.get()}'

    def set(self, value):
        if type(value) != int:
            raise ValueInvalid(value)

        if value < 0:
            raise ValueOutOfBounds(value)
        if value > MAX_EIGHT_BIT_VALUE:
            raise ValueOutOfBounds(value)

        self.high_reg.set(value >> 4)
        self.low_reg.set(value & 0x0F)

    def get(self):
        value = self.high_reg.get() << 4
        value += self.low_reg.get()
        return value


# Intel4004 also has one real eight bit register
class EightBitRegister(Register):
    num_bits = 8

    def __init__(self, name, value=0):
        super().__init__(name, MAX_EIGHT_BIT_VALUE)
        self.set(value)

    def __repr__(self):
        return f'Eight bit register {self.name} with value {self.get()}'


# The Intel4004 program counter is a 12 bit register. Yes really. It does not
# pretend to be backed by three four bit registers though.
class TwelveBitRegister(Register):
    num_bits = 12

    def __init__(self, name, value=0):
        super().__init__(name, MAX_TWELVE_BIT_VALUE)
        self.set(value)

    def __repr__(self):
        return f'Twelve bit register {self.name} with value {self.get()}'
