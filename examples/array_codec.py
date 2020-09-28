import array
import sys
from binascii import unhexlify
from pprint import pprint

import cbor2


def is_float(tag):
    return tag >> 4 & 1


def is_signed(tag):
    return tag >> 3 & 1


def is_le(tag):
    return tag >> 2 & 1


def needs_swap(tag):
    length = tag & 0b11
    if is_float(tag) == 0 and length == 0:
        return False
    if sys.byteorder == 'big':
        return is_le(tag)
    else:
        return not is_le(tag)


def tag_to_type(tag):
    int_typecodes = ['B', 'H', 'L', 'Q']
    sint_typecodes = [n.lower() for n in int_typecodes]
    float_typecodes = [None, 'f', 'd', None]
    length = tag & 0b11
    if is_float(tag):
        return float_typecodes[length]
    elif is_signed(tag):
        return sint_typecodes[length]
    else:
        return int_typecodes[length]


def create_encode_map():
    encode_map = {}
    for tag in ARRAY_TAGS:
        if needs_swap(tag):
            continue
        typecode = tag_to_type(tag)
        if typecode is None:
            continue
        if typecode not in encode_map:
            encode_map[typecode] = tag
    return encode_map


ARRAY_TAGS = range(64, 88)
ENCODE_MAP = create_encode_map()


def default(encoder, obj):
    if isinstance(obj, array.array):
        tag = ENCODE_MAP[obj.typecode]
        encoder.encode(cbor2.CBORTag(tag, obj.tobytes()))
    elif isinstance(obj, memoryview):
        tag = ENCODE_MAP[obj.format]
        encoder.encode(cbor2.CBORTag(tag, obj.tobytes()))


def my_hook(decoder, tag):
    if tag.tag in ARRAY_TAGS:
        dtype = tag_to_type(tag.tag)
        if dtype is None:
            return tag
        value = array.array(dtype, tag.value)
        if needs_swap(tag.tag):
            value.byteswap()
        return value
    else:
        return tag


def selftest():
    mydata = {
        'sint8': array.array('b', range(-3, 1)),
        'uint8': array.array('B', range(3)),
        'uint16': array.array('H', [n + 128 for n in range(3)]),
        'sint16': array.array('h', [n - 256 for n in range(3)]),
        'sint32': array.array('l', [n - 2 ** 15 for n in range(3)]),
        'uint32': array.array('L', [n + 2 ** 16 for n in range(3)]),
        'uint64': array.array('Q', [n + 2 ** 32 for n in range(3)]),
        'sint64': array.array('q', [n - 2 ** 31 for n in range(3)]),
        'float32': array.array('f', [2 ** (1 / n) for n in range(1, 4)]),
        'float64': array.array('d', [2 ** (1 / n) for n in range(1, 4)]),
    }

    pprint(cbor2.loads(cbor2.dumps(mydata, default=default), tag_hook=my_hook))
    pprint(ENCODE_MAP)

    pprint(cbor2.loads(cbor2.dumps(cbor2.CBORTag(87, bytes(16))), tag_hook=my_hook))

    pprint(cbor2.loads(unhexlify(b'd8514c400000003fb504f33fa14518'), tag_hook=my_hook))


if __name__ == '__main__':
    selftest()
