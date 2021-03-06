# encoding: utf8

import logging
import sys
import traceback

import clang.cindex as clidx

from genutil import *
from typeconv import TypeConv, TypeConvertContext


# 类型转换规则
# 原始类型指针、引用
# 原始类型非指针、非引用
# char*类型
# qt类型指针，引用
# qt类型非指针，非引用

# 还需要分返回值的类型


class TypeConvForGo(TypeConv):
    def __init__(self):
        super(TypeConvForGo, self).__init__()
        return

    def ArgType2GoReflectType(self, cxxtype, cursor):
        ctx = self.createContext(cxxtype, cursor)

        if ctx.convable_type.kind == clidx.TypeKind.BOOL:
            return 'qtrt.BoolTy(false)'
        if ctx.convable_type.kind == clidx.TypeKind.USHORT \
           or ctx.convable_type.kind == clidx.TypeKind.SHORT:
            return 'qtrt.Int16Ty(false)'
        if ctx.convable_type.kind == clidx.TypeKind.INT \
           or ctx.convable_type.kind == clidx.TypeKind.UINT \
           or ctx.convable_type.kind == clidx.TypeKind.LONG \
           or ctx.convable_type.kind == clidx.TypeKind.ULONG:
            return 'qtrt.Int32Ty(false)'
        if ctx.convable_type.kind == clidx.TypeKind.ULONGLONG \
           or ctx.convable_type.kind == clidx.TypeKind.LONGLONG:
            return 'qtrt.Int64Ty(false)'

        if ctx.convable_type.kind == clidx.TypeKind.DOUBLE:
            return 'qtrt.DoubleTy(false)'
        if ctx.convable_type.kind == clidx.TypeKind.FLOAT:
            return 'qtrt.FloatTy(false)'

        if ctx.convable_type.kind == clidx.TypeKind.UCHAR \
           or ctx.convable_type.kind == clidx.TypeKind.CHAR_S:
            return 'qtrt.ByteTy(false)'

        if ctx.convable_type.kind == clidx.TypeKind.ENUM:
            return 'qtrt.Int32Ty(false)'

        if ctx.convable_type.kind == clidx.TypeKind.LVALUEREFERENCE:
            if ctx.can_type_name.startswith('Q'):
                cmod = self.gutil.get_decl_mod(cursor)
                tmod = self.gutil.get_decl_mod(ctx.can_type.get_declaration())
                if cmod != tmod:
                    return 'reflect.TypeOf(qt%s.%s{})' % (tmod, ctx.can_type_name)
                else:
                    return 'reflect.TypeOf(%s{})' % (ctx.can_type_name)
            if ctx.can_type.kind == clidx.TypeKind.CHAR_S:
                return 'qtrt.StringTy(false)'
            if ctx.can_type.kind == clidx.TypeKind.UINT \
               or ctx.can_type.kind == clidx.TypeKind.INT:
                return 'qtrt.Int32Ty(false)'
            if ctx.can_type.kind == clidx.TypeKind.USHORT \
               or ctx.can_type.kind == clidx.TypeKind.SHORT:
                return 'qtrt.FloatTy(false)'
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.RVALUEREFERENCE:
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                cmod = self.gutil.get_decl_mod(cursor)
                tmod = self.gutil.get_decl_mod(ctx.can_type.get_declaration())
                if cmod != tmod:
                    return 'reflect.TypeOf(qt%s.%s{})' % (tmod, ctx.can_type_name)
                else:
                    return 'reflect.TypeOf(%s{})' % (ctx.can_type_name)
            self.dumpContext(ctx)
        if ctx.convable_type.kind == clidx.TypeKind.RECORD:
            cmod = self.gutil.get_decl_mod(cursor)
            tmod = self.gutil.get_decl_mod(ctx.can_type.get_declaration())
            if cmod != tmod:
                return 'reflect.TypeOf(qt%s.%s{})' % (tmod, ctx.can_type_name)
            else:
                return 'reflect.TypeOf(%s{})' % (ctx.can_type_name)

        if ctx.convable_type.kind == clidx.TypeKind.POINTER:
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                # TODO like QListData::Data
                # if '::' not in ctx.can_type_name:
                cmod = self.gutil.get_decl_mod(cursor)
                tmod = self.gutil.get_decl_mod(ctx.can_type.get_declaration())
                if cmod != tmod:
                    return 'reflect.TypeOf(qt%s.%s{})' % (tmod, ctx.can_type_name)
                else:
                    return 'reflect.TypeOf(%s{})' % (ctx.can_type_name)
                self.dumpContext(ctx)
            if ctx.can_type.kind == clidx.TypeKind.BOOL:
                return 'qtrt.BoolTy(true)'
            if ctx.can_type.kind == clidx.TypeKind.CHAR_S \
               or ctx.can_type.kind == clidx.TypeKind.UCHAR:
                return 'qtrt.ByteTy(true)'
            if ctx.can_type.kind == clidx.TypeKind.CHAR32:
                return 'qtrt.RuneTy(true)'
            if ctx.can_type.kind == clidx.TypeKind.CHAR16:
                return 'qtrt.RuneTy(true)'
            if ctx.can_type.kind == clidx.TypeKind.WCHAR:
                return 'qtrt.RuneTy(true)'
            if ctx.can_type.kind == clidx.TypeKind.USHORT \
               or ctx.can_type.kind == clidx.TypeKind.SHORT:
                return 'qtrt.Int16Ty(true)'
            if ctx.can_type.kind == clidx.TypeKind.UINT \
               or ctx.can_type.kind == clidx.TypeKind.INT:
                return 'qtrt.Int32Ty(true)'
            if ctx.can_type.kind == clidx.TypeKind.ENUM:
                return 'qtrt.Int32Ty(true)'
            if ctx.can_type.kind == clidx.TypeKind.FLOAT:
                return 'qtrt.FloatTy(true)'
            if ctx.can_type.kind == clidx.TypeKind.DOUBLE:
                return 'qtrt.DoubleTy(true)'
            if ctx.can_type.kind == clidx.TypeKind.ULONGLONG \
               or ctx.can_type.kind == clidx.TypeKind.LONGLONG:
                return 'qtrt.Int64Ty(true)'
            if ctx.can_type.kind == clidx.TypeKind.ULONG \
               or ctx.can_type.kind == clidx.TypeKind.LONG:
                return 'qtrt.Int32Ty(true)'
            if ctx.can_type.kind == clidx.TypeKind.VOID:
                return 'qtrt.VoidpTy()'
            if ctx.can_type.kind == clidx.TypeKind.FUNCTIONPROTO:
                return 'qtrt.VoidpTy()'
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.FUNCTIONPROTO:
            return 'qtrt.VoidpTy()'
        if ctx.convable_type.kind == clidx.TypeKind.MEMBERPOINTER:
            return 'qtrt.VoidpTy()'

        if ctx.convable_type.kind == clidx.TypeKind.UNEXPOSED:
            if ctx.can_type.kind == clidx.TypeKind.ENUM:
                return 'qtrt.Int32Ty(false)'
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                if ctx.can_type_name.startswith('QFlags<'):
                    return 'qtrt.Int64Ty(false)'
                if 'Flags<' in ctx.can_type_name:
                    return 'qtrt.Int64Ty(false)'
                # TODO
                if ctx.can_type_name.startswith('QList<'):
                    return 'qtrt.VoidpTy()'
                if ctx.can_type_name.startswith('QVector<'):
                    return 'qtrt.VoidpTy()'
                if ctx.can_type_name.startswith('std::initializer_list<'):
                    return 'qtrt.VoidpTy()'
                if '::' in ctx.can_type_name:
                    return 'qtrt.Int32Ty(false)'
                self.dumpContext(ctx)
            if ctx.convable_type_name.startswith('::quintptr'):  # should be WId
                return 'qtrt.Int32Ty(true)'
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.CONSTANTARRAY:
            return 'qtrt.VoidpTy()'
        if ctx.convable_type.kind == clidx.TypeKind.INCOMPLETEARRAY:
            dim = self.ArrayDim(ctx.convable_type)
            return 'qtrt.VoidpTy()'

        if ctx.orig_type.kind == clidx.TypeKind.TYPEDEF:
            return self.ArgType2GoReflectType(ctx.can_type, cursor)

        self.dumpContext(ctx)
        return

    def ArgType2FFIExt(self, cxxtype, cursor):
        ctx = self.createContext(cxxtype, cursor)

        if ctx.convable_type.kind == clidx.TypeKind.BOOL:
            return 'bool'
        if ctx.convable_type.kind == clidx.TypeKind.SHORT \
           or ctx.convable_type.kind == clidx.TypeKind.USHORT:
            return 'int16_t'
        if ctx.convable_type.kind == clidx.TypeKind.INT \
           or ctx.convable_type.kind == clidx.TypeKind.UINT \
           or ctx.convable_type.kind == clidx.TypeKind.LONG \
           or ctx.convable_type.kind == clidx.TypeKind.ULONG:
            return 'int32_t'
        if ctx.convable_type.kind == clidx.TypeKind.ULONGLONG \
           or ctx.convable_type.kind == clidx.TypeKind.LONGLONG:
            return 'int64_t'

        if ctx.convable_type.kind == clidx.TypeKind.DOUBLE:
            return ctx.convable_type.spelling
        if ctx.convable_type.kind == clidx.TypeKind.FLOAT:
            return ctx.convable_type.spelling

        if ctx.convable_type.kind == clidx.TypeKind.CHAR_S \
           or ctx.convable_type.kind == clidx.TypeKind.UCHAR:
            return 'unsigned char'

        if ctx.convable_type.kind == clidx.TypeKind.ENUM:
            return 'int32_t'

        if ctx.convable_type.kind == clidx.TypeKind.LVALUEREFERENCE:
            if ctx.can_type_name.startswith('Q'):
                return 'void*'
            if ctx.can_type.kind == clidx.TypeKind.CHAR_S \
               or ctx.can_type.kind == clidx.TypeKind.UCHAR:
                return 'void*'  # 'unsigned char*'
            if ctx.can_type.kind == clidx.TypeKind.ULONGLONG \
               or ctx.can_type.kind == clidx.TypeKind.LONGLONG:
                return 'void*'  # 'int64_t*'
            if ctx.can_type.kind == clidx.TypeKind.UINT \
               or ctx.can_type.kind == clidx.TypeKind.INT:
                return 'void*'  # 'int32_t*'
            if ctx.can_type.kind == clidx.TypeKind.USHORT \
               or ctx.can_type.kind == clidx.TypeKind.SHORT:
                return 'void*'  # 'int16_t*'
            if ctx.can_type.kind == clidx.TypeKind.DOUBLE:
                return 'void*'  # 'double*'
            if ctx.can_type.kind == clidx.TypeKind.FLOAT:
                return 'void*'  # 'float*'
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.RVALUEREFERENCE:
            if ctx.can_type_name.startswith('Q'):
                return 'void*'
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.RECORD:
            return 'void*'

        if ctx.convable_type.kind == clidx.TypeKind.POINTER:
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                # TODO like QListData::Data
                # if '::' not in ctx.can_type_name:
                return 'void*'
                self.dumpContext(ctx)
            if ctx.can_type.kind == clidx.TypeKind.BOOL:
                return 'void*'  # 'bool*'
            if ctx.can_type.kind == clidx.TypeKind.CHAR_S \
               or ctx.can_type.kind == clidx.TypeKind.UCHAR:
                return 'void*'  # 'unsigned char*'
            if ctx.can_type.kind == clidx.TypeKind.WCHAR:
                return 'void*'  # 'wchar_t*'
            if ctx.can_type.kind == clidx.TypeKind.CHAR32:
                return 'void*'  # '%s*' % (ctx.can_type_name)
            if ctx.can_type.kind == clidx.TypeKind.CHAR16:
                return 'void*'  # '%s*' % (ctx.can_type_name)
            if ctx.can_type.kind == clidx.TypeKind.USHORT \
               or ctx.can_type.kind == clidx.TypeKind.SHORT:
                return 'void*'  # 'int16_t*'
            if ctx.can_type.kind == clidx.TypeKind.UINT \
               or ctx.can_type.kind == clidx.TypeKind.INT:
                return 'void*'  # 'int32_t*'
            if ctx.can_type.kind == clidx.TypeKind.FLOAT:
                return 'void*'  # '%s*' % (ctx.can_type_name)
            if ctx.can_type.kind == clidx.TypeKind.DOUBLE:
                return 'void*'  # '%s*' % (ctx.can_type_name)
            if ctx.can_type.kind == clidx.TypeKind.ULONGLONG \
               or ctx.can_type.kind == clidx.TypeKind.LONGLONG:
                return 'void*'  # 'int64_t*'
            if ctx.can_type.kind == clidx.TypeKind.ULONG \
               or ctx.can_type.kind == clidx.TypeKind.LONG:
                return 'void*'  # 'int32_t*'
            if ctx.can_type.kind == clidx.TypeKind.ENUM:
                return 'void*'  # 'int32_t*'
            if ctx.can_type.kind == clidx.TypeKind.VOID:
                return 'void*'
            # TODO
            if ctx.can_type.kind == clidx.TypeKind.FUNCTIONPROTO:
                return 'void*'
            self.dumpContext(ctx)

        # TODO memory overflow
        if ctx.convable_type.kind == clidx.TypeKind.MEMBERPOINTER:
            return 'void*'
        # TODO
        if ctx.convable_type.kind == clidx.TypeKind.FUNCTIONPROTO:
            return ctx.convable_type.spelling

        # return cursor's type
        def get_unexport_decl(uty):
            return

        # TODO UNEXPOSED 类型是不是应该试着查找类型定义的地方
        if ctx.convable_type.kind == clidx.TypeKind.UNEXPOSED:
            if ctx.can_type.kind == clidx.TypeKind.ENUM:
                return 'int32_t'
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                if ctx.can_type_name.startswith('QFlags<'):
                    return 'void*'
                if 'Flags<' in ctx.can_type_name:
                    return 'void*'
                # TODO
                if ctx.can_type_name.startswith('QList<'):
                    return 'void*'
                if ctx.can_type_name.startswith('QVector<'):
                    return 'void*'
                if ctx.can_type_name.startswith('QPair<'):
                    return 'void*'
                if ctx.can_type_name.startswith('QMap<'):
                    return 'void*'
                if ctx.can_type_name.startswith('QHash<'):
                    return 'void*'
                if ctx.can_type_name.startswith('QSet<'):
                    return 'void*'
                if ctx.can_type_name.startswith('std::initializer_list<'):
                    return 'void*'
                if '::' in ctx.can_type_name:
                    return 'void*'
                if 'Matrix<' in ctx.can_type_name:
                    return 'void*'
                if '<' in ctx.can_type_name and '>' in ctx.can_type_name:
                    return 'void*'
                self.dumpContext(ctx)
            if ctx.convable_type_name.startswith('QAccessible::Id'):
                return 'uint32_t'
            if ctx.convable_type_name.startswith('Qt::HANDLE'):
                return 'void*'
            if ctx.convable_type_name.startswith('::quintptr'):  # should be WId
                return 'void*'  # 'int32_t*'
            if ctx.convable_type_name == 'std::string':
                return 'void*'  # 'char*'
            if ctx.convable_type_name == 'std::wstring':
                return 'void*'  # 'wchar_t*'
            if ctx.convable_type_name == 'std::w32string':
                return 'void*'  # 'wchar_t*'
            if ctx.convable_type_name == 'std::u32string':
                return 'void*'  # 'wchar_t*'
            if ctx.convable_type_name == 'std::u16string':
                return 'void*'  # 'wchar_t*'

            self.dumpContext(ctx)

        # TODO 数组维度
        if ctx.convable_type.kind == clidx.TypeKind.CONSTANTARRAY:
            adim = self.ArrayDim(ctx.convable_type)
            return 'void%s' % (''.zfill(adim).replace('0', '*'))
            # return '%s%s' % (ctx.can_type_name.split(' ')[0], ''.zfill(adim).replace('0', '*'))
        if ctx.convable_type.kind == clidx.TypeKind.INCOMPLETEARRAY:
            adim = self.ArrayDim(ctx.convable_type)
            return 'void%s' % (''.zfill(adim).replace('0', '*'))
            # return '%s%s' % (ctx.can_type_name.split(' ')[0], ''.zfill(adim).replace('0', '*'))

        if ctx.orig_type.kind == clidx.TypeKind.TYPEDEF:
            return self.ArgType2FFIExt(ctx.can_type, cursor)

        # for return type
        if ctx.convable_type.kind == clidx.TypeKind.VOID: return 'void'

        self.dumpContext(ctx)
        return

    def Byte2Charp(self):
        return '(*C.uchar)((unsafe.Pointer)(reflect.ValueOf(%s.([]byte)).Pointer()))'

    def Rune2WCharp(self):
        return '(*C.wchar_t)((unsafe.Pointer)(reflect.ValueOf(%s.([]rune)).Pointer()))'

    def AnyArr2Pointer(self, cty, goty):
        return '(**C.%s)((unsafe.Pointer)(reflect.ValueOf(%%s.([][]%s)).Pointer()))' % (cty, goty)

    def ArgType2CGO(self, cxxtype, cursor):
        ctx = self.createContext(cxxtype, cursor)

        if ctx.convable_type.kind == clidx.TypeKind.BOOL:
            return 'C.bool(%s.(bool))'
        if ctx.convable_type.kind == clidx.TypeKind.USHORT \
           or ctx.convable_type.kind == clidx.TypeKind.SHORT:
            return 'C.int16_t(qtrt.PrimConv(%s, qtrt.Int16Ty(false)).(int16))'
        if ctx.convable_type.kind == clidx.TypeKind.INT \
           or ctx.convable_type.kind == clidx.TypeKind.UINT \
           or ctx.convable_type.kind == clidx.TypeKind.LONG \
           or ctx.convable_type.kind == clidx.TypeKind.ULONG:
            return 'C.int32_t(qtrt.PrimConv(%s, qtrt.Int32Ty(false)).(int32))'
        if ctx.convable_type.kind == clidx.TypeKind.ULONGLONG \
           or ctx.convable_type.kind == clidx.TypeKind.LONGLONG:
            return 'C.int64_t(qtrt.PrimConv(%s, qtrt.Int64Ty(false)).(int64))'

        if ctx.convable_type.kind == clidx.TypeKind.DOUBLE:
            return 'C.double(qtrt.PrimConv(%s, qtrt.DoubleTy(false)).(float64))'
        if ctx.convable_type.kind == clidx.TypeKind.FLOAT:
            return 'C.float(qtrt.PrimConv(%s, qtrt.FloatTy(false)).(float32))'

        if ctx.convable_type.kind == clidx.TypeKind.UCHAR \
           or ctx.convable_type.kind == clidx.TypeKind.CHAR_S:
            return 'C.uchar(%s.(byte))'

        if ctx.convable_type.kind == clidx.TypeKind.ENUM:
            return 'C.int32_t(qtrt.PrimConv(%s, qtrt.Int32Ty(false)).(int32))'

        if ctx.convable_type.kind == clidx.TypeKind.LVALUEREFERENCE:
            if ctx.can_type_name.startswith('Q'):
                cmod = self.gutil.get_decl_mod(cursor)
                tmod = self.gutil.get_decl_mod(ctx.can_type.get_declaration())
                if cmod != tmod:
                    return '%%s.(*qt%s.%s).Qclsinst' % (tmod, ctx.can_type_name)
                else:
                    return '%%s.(*%s).Qclsinst' % (ctx.can_type_name)
            if ctx.can_type.kind == clidx.TypeKind.CHAR_S:
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return self.Byte2Charp()  # 'qtrt.Byte2Charp(%s)'
            if ctx.can_type.kind == clidx.TypeKind.ULONGLONG \
               or ctx.can_type.kind == clidx.TypeKind.LONGLONG:
                return '(unsafe.Pointer)(%s.(*int64))'
                # return '(*C.int64_t)(%s.(*int64))'
            if ctx.can_type.kind == clidx.TypeKind.UINT \
               or ctx.can_type.kind == clidx.TypeKind.INT:
                return '(unsafe.Pointer)(%s.(*int32))'
                # return '(*C.int32_t)(%s.(*int32))'
            if ctx.can_type.kind == clidx.TypeKind.USHORT \
               or ctx.can_type.kind == clidx.TypeKind.SHORT:
                return '(unsafe.Pointer)(%s.(*int16))'
                # return '(*C.int16_t*)(%s.(*int16))'
            if ctx.can_type.kind == clidx.TypeKind.DOUBLE:
                return '(unsafe.Pointer)(%s.(*float64))'
                # return '(*C.double)(%s.(*float64))'
            if ctx.can_type.kind == clidx.TypeKind.FLOAT:
                return '(unsafe.Pointer)(%s.(*float32))'
                # return '(*C.float)(%s.(*float32))'
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.RVALUEREFERENCE:
            if ctx.can_type_name.startswith('Q'):
                cmod = self.gutil.get_decl_mod(cursor)
                tmod = self.gutil.get_decl_mod(ctx.can_type.get_declaration())
                if cmod != tmod:
                    return '%%s.(*qt%s.%s).Qclsinst' % (tmod, ctx.can_type_name)
                else:
                    return '%%s.(*%s).Qclsinst' % (ctx.can_type_name)
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.RECORD:
            cmod = self.gutil.get_decl_mod(cursor)
            tmod = self.gutil.get_decl_mod(ctx.can_type.get_declaration())
            if cmod != tmod:
                return '%%s.(*qt%s.%s).Qclsinst' % (tmod, ctx.can_type_name)
            else:
                return '%%s.(*%s).Qclsinst' % (ctx.can_type_name)

        if ctx.convable_type.kind == clidx.TypeKind.POINTER:
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                # TODO like QListData::Data
                # if '::' not in ctx.can_type_name:
                cmod = self.gutil.get_decl_mod(cursor)
                tmod = self.gutil.get_decl_mod(ctx.can_type.get_declaration())
                if cmod != tmod:
                    return '%%s.(*qt%s.%s).Qclsinst' % (tmod, ctx.can_type_name)
                else:
                    return '%%s.(*%s).Qclsinst' % (ctx.can_type_name)
                self.dumpContext(ctx)
            if ctx.can_type.kind == clidx.TypeKind.BOOL:
                return '(unsafe.Pointer)(%s.(*bool))'
                # return '(*C.bool)(%s.(*bool))'
            if ctx.can_type.kind == clidx.TypeKind.CHAR_S \
               or ctx.can_type.kind == clidx.TypeKind.UCHAR:
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return self.Byte2Charp()  # 'qtrt.Byte2Charp(%s)'
            if ctx.can_type.kind == clidx.TypeKind.WCHAR:
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return self.Rune2WCharp()  # '(*C.wchar_t)(%s.(*rune))'
            if ctx.can_type.kind == clidx.TypeKind.CHAR32:
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return 'C.CString(%s.(string))'
            if ctx.can_type.kind == clidx.TypeKind.CHAR16:
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return 'C.CString(%s.(string))'
            if ctx.can_type.kind == clidx.TypeKind.USHORT \
               or ctx.can_type.kind == clidx.TypeKind.SHORT:
                return '(unsafe.Pointer)(%s.(*int16))'
                # return '(*C.int16_t)(%s.(*int16))'
            if ctx.can_type.kind == clidx.TypeKind.UINT \
               or ctx.can_type.kind == clidx.TypeKind.INT:
                return '(unsafe.Pointer)(%s.(*int32))'
                # return '(*C.int32_t)(%s.(*int32))'
            if ctx.can_type.kind == clidx.TypeKind.FLOAT:
                return '(unsafe.Pointer)(%s.(*float32))'
                # return '(*C.float)(%s.(*float32))'
            if ctx.can_type.kind == clidx.TypeKind.DOUBLE:
                return '(unsafe.Pointer)(%s.(*float64))'
                # return '(*C.double)(%s.(*float64))'
            if ctx.can_type.kind == clidx.TypeKind.ULONGLONG \
               or ctx.can_type.kind == clidx.TypeKind.LONGLONG:
                return '(unsafe.Pointer)(%s.(*int64))'
                # return '(*C.int64_t)(%s.(*int64))'
            if ctx.can_type.kind == clidx.TypeKind.ULONG \
               or ctx.can_type.kind == clidx.TypeKind.LONG:
                return '(unsafe.Pointer)(%s.(*int32))'
                # return '(*C.int32_t)(%s.(*int32))'
            if ctx.can_type.kind == clidx.TypeKind.ENUM:
                return '(unsafe.Pointer)(%s.(*int32))'
                # return '(*C.int32_t)(%s.(*int32))'
            if ctx.can_type.kind == clidx.TypeKind.VOID:
                return '%s.(unsafe.Pointer)'
            # TODO
            if ctx.can_type.kind == clidx.TypeKind.FUNCTIONPROTO:
                return '%s.(unsafe.Pointer)'
            self.dumpContext(ctx)

        # TODO memory overflow
        if ctx.convable_type.kind == clidx.TypeKind.MEMBERPOINTER:
            return '%s.(unsafe.Pointer)'
        # TODO
        if ctx.convable_type.kind == clidx.TypeKind.FUNCTIONPROTO:
            return '%s.(unsafe.Pointer)'

        # return cursor's type
        def get_unexport_decl(uty):
            return

        # TODO UNEXPOSED 类型是不是应该试着查找类型定义的地方
        if ctx.convable_type.kind == clidx.TypeKind.UNEXPOSED:
            if ctx.can_type.kind == clidx.TypeKind.ENUM:
                return 'C.int32_t(%s.(int32))'
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                if ctx.can_type_name.startswith('QFlags<'):
                    return '%s.(unsafe.Pointer)'
                if 'Flags<' in ctx.can_type_name:
                    return '%s.(unsafe.Pointer)'
                # TODO
                if ctx.can_type_name.startswith('QList<'):
                    return '%s.(unsafe.Pointer)'
                if ctx.can_type_name.startswith('QVector<'):
                    return '%s.(unsafe.Pointer)'
                if ctx.can_type_name.startswith('QPair<'):
                    return '%s.(unsafe.Pointer)'
                if ctx.can_type_name.startswith('QMap<'):
                    return '%s.(unsafe.Pointer)'
                if ctx.can_type_name.startswith('QHash<'):
                    return '%s.(unsafe.Pointer)'
                if ctx.can_type_name.startswith('QSet<'):
                    return '%s.(unsafe.Pointer)'
                if ctx.can_type_name.startswith('std::initializer_list<'):
                    return '%s.(unsafe.Pointer)'
                if '::' in ctx.can_type_name:
                    return '%s.(unsafe.Pointer)'
                if 'Matrix<' in ctx.can_type_name:
                    return '%s.(unsafe.Pointer)'
                self.dumpContext(ctx)
            if ctx.convable_type_name.startswith('QAccessible::Id'):
                return 'C.int32_t(%s.(int32))'
            if ctx.convable_type_name.startswith('Qt::HANDLE'):
                return '%s.(unsafe.Pointer)'
            if ctx.convable_type_name.startswith('::quintptr'):
                return '(unsafe.Pointer)(%s.(*int32))'
                # return '(*C.int32_t)(%s.(*int32))'
            if ctx.convable_type_name == 'std::string':
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return 'C.CString(%s.(string))'
            if ctx.convable_type_name == 'std::wstring':
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return 'C.CString(%s.(string))'
            if ctx.convable_type_name == 'std::w32string':
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return 'C.CString(%s.(string))'
            if ctx.convable_type_name == 'std::u32string':
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return 'C.CString(%s.(string))'
            if ctx.convable_type_name == 'std::u16string':
                return 'qtrt.HandyConvert2c(%s, %s)'
                # return 'C.CString(%s.(string))'

            self.dumpContext(ctx)

        # TODO 数组维度
        if ctx.convable_type.kind == clidx.TypeKind.CONSTANTARRAY:
            adim = self.ArrayDim(ctx.convable_type)
            # return '%s%s' % (ctx.can_type_name.split(' ')[0], ''.zfill(adim).replace('0', '*'))
            cty = ctx.can_type_name.split(' ')[0]
            if adim == 2 and cty == 'float':
                return self.AnyArr2Pointer(cty, 'float32')
            if adim == 2 and cty == 'double':
                return self.AnyArr2Pointer(cty, 'float64')
            self.dumpContext(ctx)
            # return '%s.(unsafe.Pointer)'
        if ctx.convable_type.kind == clidx.TypeKind.INCOMPLETEARRAY:
            adim = self.ArrayDim(ctx.convable_type)
            # return '%s%s' % (ctx.can_type_name.split(' ')[0], ''.zfill(adim).replace('0', '*'))
            cty = ctx.can_type_name.split(' ')[0]
            if adim == 2 and cty == 'float':
                return self.AnyArr2Pointer(cty, 'float32')
            if adim == 2 and cty == 'double':
                return self.AnyArr2Pointer(cty, 'float64')
            if adim == 2 and cty == 'char':
                return 'C.CString(%s.(string))'
            self.dumpContext(ctx)
            # return '%s.(unsafe.Pointer)'

        if ctx.orig_type.kind == clidx.TypeKind.TYPEDEF:
            return self.ArgType2FFIExt(ctx.can_type, cursor)

        # for return type
        if ctx.convable_type.kind == clidx.TypeKind.VOID: return ''

        self.dumpContext(ctx)
        return

    def ArgType2Go(self, cxxtype, cursor):
        ctx = self.createContext(cxxtype, cursor)

        if ctx.convable_type.kind == clidx.TypeKind.BOOL:
            return 'bool'
        if ctx.convable_type.kind == clidx.TypeKind.SHORT \
           or ctx.convable_type.kind == clidx.TypeKind.USHORT:
            return 'int16'
        if ctx.convable_type.kind == clidx.TypeKind.INT \
           or ctx.convable_type.kind == clidx.TypeKind.UINT \
           or ctx.convable_type.kind == clidx.TypeKind.LONG \
           or ctx.convable_type.kind == clidx.TypeKind.ULONG:
            return 'int32'
        if ctx.convable_type.kind == clidx.TypeKind.LONGLONG \
           or ctx.convable_type.kind == clidx.TypeKind.ULONGLONG:
            return 'int64'
        if ctx.convable_type.kind == clidx.TypeKind.DOUBLE:
            return 'float64'
        if ctx.convable_type.kind == clidx.TypeKind.FLOAT:
            return 'float32'
        if ctx.convable_type.kind == clidx.TypeKind.UCHAR \
           or ctx.convable_type.kind == clidx.TypeKind.CHAR_S:
            return 'byte'
        if ctx.convable_type.kind == clidx.TypeKind.ENUM:
            return 'int32'

        if ctx.convable_type.kind == clidx.TypeKind.LVALUEREFERENCE:
            if ctx.can_type_name.startswith('Q'):
                return '%s' % (ctx.can_type_name)
            if ctx.can_type.kind == clidx.TypeKind.CHAR_S \
               or ctx.can_type.kind == clidx.TypeKind.UCHAR:
                return '[]byte'
            if ctx.can_type.kind == clidx.TypeKind.ULONGLONG \
               or ctx.can_type.kind == clidx.TypeKind.LONGLONG:
                return 'int64'
            if ctx.can_type.kind == clidx.TypeKind.UINT \
               or ctx.can_type.kind == clidx.TypeKind.INT:
                return 'int32'
            if ctx.can_type.kind == clidx.TypeKind.USHORT \
               or ctx.can_type.kind == clidx.TypeKind.SHORT:
                return 'int16'
            if ctx.can_type.kind == clidx.TypeKind.DOUBLE:
                return 'float64'
            if ctx.can_type.kind == clidx.TypeKind.FLOAT:
                return 'float32'
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.RVALUEREFERENCE:
            if ctx.can_type_name.startswith('Q'):
                return '%s' % (ctx.can_type_name)
            self.dumpContext(ctx)

        if ctx.convable_type.kind == clidx.TypeKind.RECORD:
            return '%s' % (ctx.can_type_name)

        if ctx.convable_type.kind == clidx.TypeKind.POINTER:
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                # TODO like QListData::Data
                # if '::' not in ctx.can_type_name:
                return '*%s' % (ctx.can_type_name)
                self.dumpContext(ctx)
            if ctx.can_type.kind == clidx.TypeKind.BOOL:
                return '*bool'
            if ctx.can_type.kind == clidx.TypeKind.CHAR_S \
               or ctx.can_type.kind == clidx.TypeKind.UCHAR:
                return '[]byte'
            if ctx.can_type.kind == clidx.TypeKind.WCHAR:
                return '[]rune'
            if ctx.can_type.kind == clidx.TypeKind.CHAR32:
                return 'string'
            if ctx.can_type.kind == clidx.TypeKind.CHAR16:
                return 'string'
            if ctx.can_type.kind == clidx.TypeKind.USHORT \
               or ctx.can_type.kind == clidx.TypeKind.SHORT:
                return '*int16'
            if ctx.can_type.kind == clidx.TypeKind.UINT \
               or ctx.can_type.kind == clidx.TypeKind.INT:
                return '*int32'
            if ctx.can_type.kind == clidx.TypeKind.FLOAT:
                return '*float32'
            if ctx.can_type.kind == clidx.TypeKind.DOUBLE:
                return '*float64'
            if ctx.can_type.kind == clidx.TypeKind.ULONGLONG \
               or ctx.can_type.kind == clidx.TypeKind.LONGLONG:
                return '*int64'
            if ctx.can_type.kind == clidx.TypeKind.ULONG \
               or ctx.can_type.kind == clidx.TypeKind.LONG:
                return '*int32'
            if ctx.can_type.kind == clidx.TypeKind.ENUM:
                return '*int32'
            if ctx.can_type.kind == clidx.TypeKind.VOID:
                return ''
            # TODO
            if ctx.can_type.kind == clidx.TypeKind.FUNCTIONPROTO:
                return 'unsafe.Pointer'
            self.dumpContext(ctx)

        # TODO memory overflow
        if ctx.convable_type.kind == clidx.TypeKind.MEMBERPOINTER:
            return 'unsafe.Pointer'
        # TODO
        if ctx.convable_type.kind == clidx.TypeKind.FUNCTIONPROTO:
            return 'unsafe.Pointer'

        # return cursor's type
        def get_unexport_decl(uty):
            return

        # TODO UNEXPOSED 类型是不是应该试着查找类型定义的地方
        if ctx.convable_type.kind == clidx.TypeKind.UNEXPOSED:
            if ctx.can_type.kind == clidx.TypeKind.ENUM:
                return ctx.convable_type.spelling
            if ctx.can_type.kind == clidx.TypeKind.RECORD:
                if ctx.can_type_name.startswith('QFlags<'):
                    return 'int64'
                if 'Flags<' in ctx.can_type_name:
                    return 'int64'
                # TODO
                if ctx.can_type_name.startswith('QList<'):
                    return 'int64'
                if ctx.can_type_name.startswith('QVector<'):
                    return 'int64'
                if ctx.can_type_name.startswith('QPair<'):
                    return 'int64'
                if ctx.can_type_name.startswith('QMap<'):
                    return 'int64'
                if ctx.can_type_name.startswith('QHash<'):
                    return 'int64'
                if ctx.can_type_name.startswith('QSet<'):
                    return 'int64'
                if ctx.can_type_name.startswith('std::initializer_list<'):
                    return 'int64'
                if '::' in ctx.can_type_name:
                    return 'int64'
                if 'Matrix<' in ctx.can_type_name:
                    return 'int64'
                self.dumpContext(ctx)
            if ctx.convable_type_name.startswith('QAccessible::Id'):
                return 'uint32'
            if ctx.convable_type_name.startswith('Qt::HANDLE'):
                return 'unsafe.Pointer'
            if ctx.convable_type_name.startswith('::quintptr'):
                return '*int32'
            if ctx.convable_type_name == 'std::string':
                return 'string'
            if ctx.convable_type_name == 'std::wstring':
                return 'string'
            if ctx.convable_type_name == 'std::w32string':
                return 'string'
            if ctx.convable_type_name == 'std::u32string':
                return 'string'
            if ctx.convable_type_name == 'std::u16string':
                return 'string'

            self.dumpContext(ctx)

        # TODO 数组维度
        if ctx.convable_type.kind == clidx.TypeKind.CONSTANTARRAY:
            adim = self.ArrayDim(ctx.convable_type)
            return '%s%s' % (''.zfill(adim).replace('0', '[]'), ctx.can_type_name.split(' ')[0])
        if ctx.convable_type.kind == clidx.TypeKind.INCOMPLETEARRAY:
            adim = self.ArrayDim(ctx.convable_type)
            return '%s%s' % (''.zfill(adim).replace('0', '[]'), ctx.can_type_name.split(' ')[0])

        if ctx.orig_type.kind == clidx.TypeKind.TYPEDEF:
            return self.ArgType2FFIExt(ctx.can_type, cursor)

        # for return type
        if ctx.convable_type.kind == clidx.TypeKind.VOID: return ''

        self.dumpContext(ctx)
        return

