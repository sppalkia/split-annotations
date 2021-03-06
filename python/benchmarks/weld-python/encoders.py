
from bindings import *
from compiled import WeldEncoder, WeldDecoder
from weldtypes import *

import numpy as np
import ctypes


def dtype_to_weld_type(dtype):
    if dtype == 'int32':
        return WeldInt()
    elif dtype == 'int64':
        return WeldLong()
    elif dtype == 'float32':
        return WeldFloat()
    elif dtype == 'float64':
        return WeldDouble()
    else:
        raise ValueError("unsupported dtype {}".format(dtype))


class NumpyArrayEncoder(WeldEncoder):

    def _check(self, obj):
        """
        Checks whether this NumPy array is supported by Weld.
        """
        assert isinstance(obj, np.ndarray)

    def encode(self, obj):
        self._check(obj)
        elem_type = dtype_to_weld_type(obj.dtype)
        c_class = WeldVec(elem_type).ctype_class
        elem_class = elem_type.ctype_class
        ptr = obj.ctypes.data_as(POINTER(elem_class))
        # obj.size gives the correct value for multi-dimensional arrays.
        size = ctypes.c_int64(obj.size)
        return c_class(ptr=ptr, size=size)

    def py_to_weld_type(self, obj):
        self._check(obj)
        return WeldVec(dtype_to_weld_type(obj.dtype))


class NumpyArrayDecoder(WeldDecoder):
    def decode(self, obj, restype):
        # This stuff is same as grizzly.
        if restype == WeldInt():
            data = WeldValue(obj).data()
            result = ctypes.cast(data, ctypes.POINTER(c_int)).contents.value
            return np.int32(result)
        elif restype == WeldLong():
            data = WeldValue(obj).data()
            result = ctypes.cast(data, ctypes.POINTER(c_long)).contents.value
            return np.int64(result)
        elif restype == WeldFloat():
            data = WeldValue(obj).data()
            result = ctypes.cast(data, ctypes.POINTER(c_float)).contents.value
            return np.float32(result)
        elif restype == WeldDouble():
            data = WeldValue(obj).data()
            result = ctypes.cast(data, ctypes.POINTER(c_double)).contents.value
            return np.float64(result) 

        # is a WeldVec() - depending on the types, need to make minor changes.
        assert isinstance(restype, WeldVec)
        obj = obj.contents
        size = obj.size
        data = obj.ptr
        dtype = restype.elemType.ctype_class

        if restype == WeldVec(WeldInt()) or restype == WeldVec(WeldFloat()):
            # these have same sizes.
            ArrayType = ctypes.c_float*size
        elif restype == WeldVec(WeldLong()) or restype == WeldVec(WeldDouble()):
            ArrayType = ctypes.c_double*size
        
        array_pointer = ctypes.cast(data, ctypes.POINTER(ArrayType))
        result = np.frombuffer(array_pointer.contents, dtype=dtype,count=size)
        return result

class StructDecoder(WeldDecoder):

    def __init__(self, types, decoders):
        for decoder in decoders:
            assert isinstance(decoder, WeldDecoder)
        for ty in types:
            assert isinstance(ty, WeldType)
        assert len(types) == len(decoders)
        self.decoders = decoders
        self.types = types
    
    def decode(self, obj, restype):
        decoded = []
        result_struct = ctypes.cast(obj, ctypes.POINTER(restype.ctype_class)).contents
        for (ty, decoder, (name, field_type)) in zip(self.types, self.decoders, result_struct._fields_):
            value = getattr(result_struct, name)
            decoded.append(decoder.decode(ctypes.pointer(value), ty))
        return tuple(decoded)

class ScalarDecoder(WeldDecoder):
    def decode(self, obj, restype):
        assert isinstance(restype, WeldLong)
        result = obj.contents.value
        return result
