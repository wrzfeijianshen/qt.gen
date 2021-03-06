# encoding: utf8

import os
import logging
import time

import clang
import clang.cindex
import clang.cindex as clidx

from genutil import *
from typeconv import TypeConv, TypeConvForRust
from genbase import GenerateBase, GenClassContext, GenMethodContext
from genfilter import GenFilterRust


class GenerateForRust(GenerateBase):
    def __init__(self):
        super(GenerateForRust, self).__init__()

        self.gfilter = GenFilterRust()
        self.modrss = {}  # mod => CodePaper
        #self.cp_modrs = CodePaper()  # 可能的name: main
        #self.cp_modrs.addPoint('main')
        #self.MP = self.cp_modrs

        self.class_blocks = ['header', 'main', 'use', 'ext', 'body']
        # self.cp_clsrs = CodePaper()  # 可能中间reset。可能的name: header, main, use, ext, body
        # self.CP = self.cp_clsrs

        self.qclses = {}  # class name => True
        self.tyconv = TypeConvForRust()
        self.traits = {}  # traits proto => True
        self.implmthods = {}  # method proto => True
        return

    def generateHeader(self, module):
        code = ''
        code += "#![feature(libc)]\n"
        code += "#![feature(core)]\n"
        code += "#![feature(collections)]\n"
        code += "extern crate libc;\n"
        code += "use self::libc::*;\n"

        code += "\n"
        return code

    def generateFooter(self, module):
        return ''

    def initCodePaperForClass(self):
        cp_clsrs = CodePaper()
        for blk in self.class_blocks:
            cp_clsrs.addPoint(blk)
            cp_clsrs.append(blk, "// %s block begin" % (blk))
        return cp_clsrs

    def genpass_init_code_paper(self):
        for key in self.gctx.codes:
            CP = self.gctx.codes[key]
            mod = self.gctx.get_decl_mod_by_path(key)
            code_file = self.gctx.get_code_file_by_path(key)
            CP.AP('header', '// auto generated, do not modify.')
            CP.AP('header', '// created: ' + time.ctime())
            CP.AP('header', '// src-file: ' + key)
            CP.AP('header', '// dst-file: /src/%s/%s.rs' % (mod, code_file))
            CP.AP('header', '//\n')

            for blk in self.class_blocks:
                CP.addPoint(blk)
                CP.append(blk, "// %s block begin =>" % (blk))
        return

    def genpass_code_header(self):
        for key in self.gctx.codes:
            CP = self.gctx.codes[key]
            CP.AP('header', self.generateHeader(''))
            CP.AP('ext', "// #[link(name = \"Qt5Core\")]")
            CP.AP('ext', "// #[link(name = \"Qt5Gui\")]")
            CP.AP('ext', "// #[link(name = \"Qt5Widgets\")]")
            CP.AP('ext', "// #[link(name = \"QtInline\")]\n")
            CP.AP('ext', "extern {")

        return

    def genpass_code_endian(self):
        for key in self.gctx.codes:
            CP = self.gctx.codes[key]
            for blk in self.class_blocks:
                if blk == 'ext':
                    CP.append(blk, "} // <= %s block end\n" % (blk))
                else:
                    CP.append(blk, "// <= %s block end\n" % (blk))

        return

    def genpass_class_modef(self):
        for key in self.gctx.classes:
            cursor = self.gctx.classes[key]
            if self.check_skip_class(cursor): continue

            ctx = GenClassContext(cursor)
            class_name = ctx.flat_class_name
            decl_file = self.gctx.get_decl_file(cursor)
            decl_mod = self.gctx.get_decl_mod(cursor)
            code_file = self.gctx.get_code_file(cursor)
            istpl = self.gctx.is_template(cursor)

            if decl_mod not in self.modrss:
                self.modrss[decl_mod] = CodePaper()
                self.modrss[decl_mod].addPoint('main')

            MP = self.modrss[decl_mod]
            MP.APU('main', "pub mod %s;" % (code_file))
            MP.APU('main', "pub use self::%s::%s;\n" % (code_file, class_name))
        return

    def genpass(self):
        self.genpass_init_code_paper()
        self.genpass_code_header()

        self.genpass_class_type()

        print('gen classes...')
        self.genpass_classes()

        print('gen signals...')
        self.genpass_classes_signals()

        print('gen code endian...')
        self.genpass_code_endian()

        print('gen class mod define...')
        self.genpass_class_modef()

        print('gen files...')
        self.genpass_write_codes()
        return

    def genpass_class_type(self):
        for key in self.gctx.classes:
            cursor = self.gctx.classes[key]
            if self.check_skip_class(cursor): continue
            self.genpass_class_type_impl(cursor)
        return

    def genpass_class_type_impl(self, cursor):
        ctx = GenClassContext(cursor)
        class_name = ctx.flat_class_name
        decl_file = self.gctx.get_decl_file(cursor)
        CP = self.gctx.codes[decl_file]
        ctysz = cursor.type.get_size()

        # TODO 计算了两遍
        bases = self.gutil.get_base_class(cursor)
        base_class = bases[0] if len(bases) > 0 else None
        usignals = self.gutil.get_unique_signals(cursor)

        CP.AP('body', "// class sizeof(%s)=%s" % (class_name, ctysz))
        # generate struct of class
        # CP.AP('body', '#[derive(Sized)]')
        CP.AP('body', '#[derive(Default)]')
        CP.AP('body', "pub struct %s {" % (class_name))
        if base_class is None:
            CP.AP('body', "  // qbase: %s," % (base_class))
        else:
            # TODO 需要use 基类
            CP.AP('body', "  qbase: %s," % (base_class.spelling))
        CP.AP('body', "  pub qclsinst: u64 /* *mut c_void*/,")
        for key in usignals:
            sigmth = usignals[key]
            CP.AP('body', '  pub _%s: %s_%s_signal,' % (sigmth.spelling, class_name, sigmth.spelling))
        CP.AP('body', "}\n")

        return

    def genpass_classes_signals(self):
        for key in self.gctx.classes:
            cursor = self.gctx.classes[key]
            if self.check_skip_class(cursor): continue

            methods = self.gutil.get_methods(cursor)
            bases = self.gutil.get_base_class(cursor)
            base_class = bases[0] if len(bases) > 0 else None
            ctx = mctx = self.createMiniContext(cursor, base_class)
            class_name = ctx.flat_class_name
            usignals = self.gutil.get_unique_signals(cursor)
            for key in usignals:
                sigmth = usignals[key]
                signame = sigmth.spelling
                if self.is_conflict_method_name(signame):
                    signame = self.fix_conflict_method_name(signame)

                ctx.CP.AP('body', '#[derive(Default)] // for %s_%s' % (class_name, signame))
                ctx.CP.AP('body', 'pub struct %s_%s_signal{poi:u64}' % (class_name, signame))

                ctx.CP.AP('body', 'impl /* struct */ %s {' % (class_name))
                ctx.CP.AP('body', '  pub fn %s(&self) -> %s_%s_signal {'
                          % (sigmth.spelling, class_name, signame))
                ctx.CP.AP('body', '     return %s_%s_signal{poi:self.qclsinst};' % (class_name, signame ))
                ctx.CP.AP('body', '  }')
                ctx.CP.AP('body', '}')

                ctx.CP.AP('body', 'impl /* struct */ %s_%s_signal {' % (class_name, signame))
                ctx.CP.AP('body', '  pub fn connect<T: %s_%s_signal_connect>(self, overload_args: T) {'
                          % (class_name, signame))
                ctx.CP.AP('body', '    overload_args.connect(self);')
                ctx.CP.AP('body', '  }')
                ctx.CP.AP('body', '}')
                ctx.CP.AP('body', 'pub trait %s_%s_signal_connect {' % (class_name, signame))
                ctx.CP.AP('body', '  fn connect(self, sigthis: %s_%s_signal);' % (class_name, signame))
                ctx.CP.AP('body', '}')
                ctx.CP.AP('body', '')

            idx = 0
            for key in ctx.signals:
                sigmth = ctx.signals[key]
                if '<' in sigmth.displayname: continue
                if self.check_skip_params(sigmth): continue
                ctx = self.createGenMethodContext(sigmth, cursor, base_class, [])

                signame = sigmth.spelling
                if self.is_conflict_method_name(signame):
                    signame = self.fix_conflict_method_name(signame)

                trait_params_array = self.generateParamsForTrait(class_name, sigmth.spelling, sigmth, ctx)
                trait_params = ', '.join(trait_params_array)
                trait_params = trait_params.replace("&'a mut ", '')
                trait_params = trait_params.replace("&'a ", '')
                if '<' in trait_params: continue  # QModelIndexList => QList<QModelIndex>
                if 'QPrivateSignal' in trait_params: continue

                params_ext_arr = self.generateParamsForExtern(class_name, sigmth.spelling, sigmth, ctx)
                params_ext = ', '.join(params_ext_arr)
                params_ext_tyarr = []
                for arg in params_ext_arr:
                    params_ext_tyarr.append(arg.split(':')[1].strip())
                params_ext_ty = ', ' .join(params_ext_tyarr)

                ctx.CP.AP('body', '// %s' % (sigmth.displayname))
                ctx.CP.AP('body', 'extern fn %s_%s_signal_connect_cb_%s(rsfptr:fn(%s), %s) {'
                          % (class_name, signame, idx, trait_params, params_ext))
                ctx.CP.AP('body', '  println!("{}:{}", file!(), line!());')
                rsargs = []
                for arg in sigmth.get_arguments():
                    sidx = len(rsargs)
                    sty = params_ext_arr[sidx]
                    dty = trait_params_array[sidx]
                    if self.is_qt_class(arg.type.spelling):
                        arg_class_name = self.get_qt_class(arg.type.spelling)
                        ctx.CP.AP('body', '  let rsarg%s = %s::inheritFrom(arg%s as u64);'
                                  % (sidx, arg_class_name, sidx))
                    else:
                        ctx.CP.AP('body', '  let rsarg%s = arg%s as %s;' % (sidx, sidx, dty))
                    rsargs.append('rsarg%s' % (sidx))

                ctx.CP.AP('body', '  rsfptr(%s);' % (','.join(rsargs)))
                ctx.CP.AP('body', '}')
                ctx.CP.AP('body', 'extern fn %s_%s_signal_connect_cb_box_%s(rsfptr_raw:*mut Box<Fn(%s)>, %s) {'
                          % (class_name, signame, idx, trait_params, params_ext))
                ctx.CP.AP('body', '  println!("{}:{}", file!(), line!());')
                ctx.CP.AP('body', '  let rsfptr = unsafe{Box::from_raw(rsfptr_raw)};')

                rsargs = []
                for arg in sigmth.get_arguments():
                    sidx = len(rsargs)
                    sty = params_ext_arr[sidx]
                    dty = trait_params_array[sidx]
                    if self.is_qt_class(arg.type.spelling):
                        arg_class_name = self.get_qt_class(arg.type.spelling)
                        ctx.CP.AP('body', '  let rsarg%s = %s::inheritFrom(arg%s as u64);'
                                  % (sidx, arg_class_name, sidx))
                    else:
                        ctx.CP.AP('body', '  let rsarg%s = arg%s as %s;' % (sidx, sidx, dty))
                    rsargs.append('rsarg%s' % (sidx))

                ctx.CP.AP('body', '  // rsfptr(%s);' % (','.join(rsargs)))
                ctx.CP.AP('body', '  unsafe{(*rsfptr_raw)(%s)};' % (','.join(rsargs)))
                ctx.CP.AP('body', '}')
                # impl xxx for fn(%s)
                ctx.CP.AP('body', 'impl /* trait */ %s_%s_signal_connect for fn(%s) {'
                          % (class_name, signame, trait_params))
                ctx.CP.AP('body', '  fn connect(self, sigthis: %s_%s_signal) {' % (class_name, signame))
                ctx.CP.AP('body', '    // do smth...')
                ctx.CP.AP('body', '    // self as u64; // error for Fn, Ok for fn')
                ctx.CP.AP('body', '    self as *mut c_void as u64;')
                ctx.CP.AP('body', '    self as *mut c_void;')
                ctx.CP.AP('body', '    let arg0 = sigthis.poi as *mut c_void;')
                ctx.CP.AP('body', '    let arg1 = %s_%s_signal_connect_cb_%s as *mut c_void;'
                          % (class_name, signame, idx))
                ctx.CP.AP('body', '    let arg2 = self as *mut c_void;')
                # ctx.CP.AP('body', '    // %s_%s_signal_connect_cb_%s' % (class_name, sigmth.spelling, idx))
                ctx.CP.AP('body', '    unsafe {%s_SlotProxy_connect_%s(arg0, arg1, arg2)};'
                          % (class_name, sigmth.mangled_name))
                ctx.CP.AP('body', '  }')
                ctx.CP.AP('body', '}')
                # impl xx for Box<fn(%s)>
                ctx.CP.AP('body', 'impl /* trait */ %s_%s_signal_connect for Box<Fn(%s)> {'
                          % (class_name, signame, trait_params))
                ctx.CP.AP('body', '  fn connect(self, sigthis: %s_%s_signal) {' % (class_name, signame))
                ctx.CP.AP('body', '    // do smth...')
                ctx.CP.AP('body', '    // Box::into_raw(self) as u64;')
                ctx.CP.AP('body', '    // Box::into_raw(self) as *mut c_void;')
                ctx.CP.AP('body', '    let arg0 = sigthis.poi as *mut c_void;')
                ctx.CP.AP('body', '    let arg1 = %s_%s_signal_connect_cb_box_%s as *mut c_void;'
                          % (class_name, signame, idx))
                ctx.CP.AP('body', '    let arg2 = Box::into_raw(Box::new(self)) as *mut c_void;')
                # ctx.CP.AP('body', '    // %s_%s_signal_connect_cb_%s' % (class_name, sigmth.spelling, idx))
                ctx.CP.AP('body', '    unsafe {%s_SlotProxy_connect_%s(arg0, arg1, arg2)};'
                          % (class_name, sigmth.mangled_name))
                ctx.CP.AP('body', '  }')
                ctx.CP.AP('body', '}')
                ctx.CP.AP('ext', '  fn %s_SlotProxy_connect_%s(qthis: *mut c_void, ffifptr: *mut c_void, rsfptr: *mut c_void);'
                          % (class_name, sigmth.mangled_name))
                idx += 1

        return

    def genpass_classes(self):
        for key in self.gctx.classes:
            cursor = self.gctx.classes[key]
            if self.check_skip_class(cursor): continue

            class_name = cursor.displayname
            methods = self.gutil.get_methods(cursor)
            bases = self.gutil.get_base_class(cursor)
            base_class = bases[0] if len(bases) > 0 else None
            self.generateClassSizeExt(cursor, base_class)
            self.generateInheritEmulate(cursor, base_class)
            self.generateClass(class_name, cursor, methods, base_class)
            # break
        return

    def generateClass(self, class_name, class_cursor, methods, base_class):

        # 重载的方法，只生成一次trait
        unique_methods = {}
        for mangled_name in methods:
            cursor = methods[mangled_name]
            isstatic = cursor.is_static_method()
            static_suffix = '_s' if isstatic else ''
            umethod_name = cursor.spelling + static_suffix
            unique_methods[umethod_name] = True

        signals = self.gutil.get_signals(class_cursor)
        dupremove = self.dedup_return_const_diff_method(methods)
        # print(444, 'dupremove len:', len(dupremove), dupremove)
        for mangled_name in methods:
            cursor = methods[mangled_name]
            method_name = cursor.spelling

            if self.check_skip_method(cursor):
                # if method_name == 'QAction':
                    #print(433, 'whyyyyyyyyyyyyyy') # no
                    # exit(0)
                continue
            if mangled_name in dupremove:
                # print(333, 'skip method:', mangled_name)
                continue
            if mangled_name in signals:
                continue

            ctx = self.createGenMethodContext(cursor, class_cursor, base_class, unique_methods)
            self.generateMethod(ctx)

        return

    def createGenMethodContext(self, method_cursor, class_cursor, base_class, unique_methods):
        ctx = GenMethodContext(method_cursor, class_cursor)
        ctx.unique_methods = unique_methods
        ctx.CP = self.gctx.getCodePager(class_cursor)

        if ctx.ctor: ctx.method_name_rewrite = 'new'
        if ctx.dtor: ctx.method_name_rewrite = 'free'
        if self.is_conflict_method_name(ctx.method_name):
            ctx.method_name_rewrite = ctx.method_name + '_'
        if ctx.static:
            ctx.method_name_rewrite = ctx.method_name + ctx.static_suffix

        ctx.isinline = self.method_is_inline(method_cursor)

        class_name = ctx.class_name
        method_name = ctx.method_name

        ctx.ret_type_name_rs = self.tyconv.Type2RustRet(ctx.ret_type, method_cursor)
        if ctx.ret_type_name_rs.count('<') > 0:
            ctx.ret_type_name_rs = self.gutil.flat_template_name(ctx.ret_type_name_rs)
        ctx.ret_type_name_ext = self.tyconv.TypeCXX2RustExtern(ctx.ret_type, method_cursor, True)

        raw_params_array = self.generateParamsRaw(class_name, method_name, method_cursor)
        raw_params = ', '.join(raw_params_array)

        trait_params_array = self.generateParamsForTrait(class_name, method_name, method_cursor, ctx)
        trait_params = ', '.join(trait_params_array)

        call_params_array = self.generateParamsForCall(class_name, method_name, method_cursor)
        call_params = ', '.join(call_params_array)
        if not ctx.static and not ctx.ctor:
            call_params = ('rsthis.qclsinst, ' + call_params).strip(' ,')

        extargs_array = self.generateParamsForExtern(class_name, method_name, method_cursor, ctx)
        extargs = ', '.join(extargs_array)
        if not ctx.static and not ctx.ctor:
            extargs = ('qthis: u64 /* *mut c_void*/, ' + extargs).strip(' ,')

        ctx.params_cpp = raw_params
        ctx.params_rs = trait_params
        ctx.params_call = call_params
        ctx.params_ext = extargs
        ctx.params_ext_arr = extargs_array

        ctx.trait_proto = '%s::%s(%s)' % (class_name, method_name, trait_params)
        ctx.fn_proto_cpp = "  // proto: %s %s %s::%s(%s);" % \
                           (ctx.static_str, ctx.ret_type_name_cpp, ctx.class_name, ctx.method_name, ctx.params_cpp)
        ctx.has_return = self.methodHasReturn(ctx)

        # base class
        ctx.base_class = base_class
        ctx.base_class_name = base_class.spelling if base_class is not None else None
        ctx.has_base = True if base_class is not None else False
        ctx.has_base = base_class is not None

        # aux
        ctx.tymap = TypeConvForRust.tymap

        return ctx

    def createMiniContext(self, cursor, base_class):
        ctx = GenClassContext(cursor)
        ctx.CP = self.gctx.getCodePager(cursor)

        # base class
        ctx.base_class = base_class
        ctx.base_class_name = base_class.spelling if base_class is not None else None
        ctx.has_base = True if base_class is not None else False
        ctx.has_base = base_class is not None

        # aux
        ctx.tymap = TypeConvForRust.tymap
        return ctx

    def generateInheritEmulate(self, cursor, base_class):
        # minictx
        ctx = self.createMiniContext(cursor, base_class)

        # ctx.CP.AP('body', '/*')
        ctx.CP.AP('body', 'impl /*struct*/ %s {' % (ctx.flat_class_name))
        ctx.CP.AP('body', '  pub fn inheritFrom(qthis: u64 /* *mut c_void*/) -> %s {' % (ctx.flat_class_name))
        if ctx.has_base:
            ctx.CP.AP('body', '    return %s{qbase: %s::inheritFrom(qthis), qclsinst: qthis, ..Default::default()};' %
                  (ctx.flat_class_name, ctx.base_class_name))
        else:
            ctx.CP.AP('body', '    return %s{qclsinst: qthis, ..Default::default()};' % (ctx.flat_class_name))
        ctx.CP.AP('body', '  }')
        ctx.CP.AP('body', '}')
        # ctx.CP.AP('body', '*/\n')

        if ctx.has_base:
            self.generateUseForRust(ctx, ctx.base_class.type, ctx.cursor)

        ctx.CP.APU('use', 'use std::ops::Deref;')

        if ctx.has_base:
            # ctx.CP.AP('body', '/*')
            ctx.CP.AP('body', 'impl Deref for %s {' % (ctx.flat_class_name))
            ctx.CP.AP('body', '  type Target = %s;' % (ctx.base_class_name))
            ctx.CP.AP('body', '')
            ctx.CP.AP('body', '  fn deref(&self) -> &%s {' % (ctx.base_class_name))
            ctx.CP.AP('body', '    return & self.qbase;')
            ctx.CP.AP('body', '  }')
            ctx.CP.AP('body', '}')
            # ctx.CP.AP('body', '*/\n')

        if ctx.has_base:
            # ctx.CP.AP('body', '/*')
            ctx.CP.AP('body', 'impl AsRef<%s> for %s {' % (ctx.base_class_name, ctx.flat_class_name))
            ctx.CP.AP('body', '  fn as_ref(& self) -> & %s {' % (ctx.base_class_name))
            ctx.CP.AP('body', '    return & self.qbase;')
            ctx.CP.AP('body', '  }')
            ctx.CP.AP('body', '}')
            # ctx.CP.AP('body', '*/\n')

        return

    def generateClassSizeExt(self, cursor, base_class):
        # minictx
        ctx = self.createMiniContext(cursor, base_class)
        ctx.CP.AP('ext', '  fn %s_Class_Size() -> c_int;' % (ctx.flat_class_name))
        return

    def generateMethod(self, ctx):
        cursor = ctx.cursor

        return_type = cursor.result_type
        return_real_type = self.real_type_name(return_type)
        if '::' in return_real_type: return
        if self.check_skip_params(cursor): return

        static_suffix = ctx.static_suffix

        # method impl
        impl_method_proto = ctx.struct_proto
        if impl_method_proto not in self.implmthods:
            self.implmthods[impl_method_proto] = True
            if ctx.ctor is True: self.generateImplStructCtor(ctx)
            else: self.generateImplStructMethod(ctx)

        uniq_method_name = cursor.spelling + static_suffix
        if ctx.unique_methods[uniq_method_name] is True:
            ctx.unique_methods[uniq_method_name] = False
            self.generateMethodDeclTrait(ctx)

        ### trait impl
        if ctx.trait_proto not in self.traits:
            self.traits[ctx.trait_proto] = True
            if ctx.ctor is True: self.generateImplTraitCtor(ctx)
            else: self.generateImplTraitMethod(ctx)

        # extern
        ctx.CP.AP('ext', ctx.fn_proto_cpp)
        self.generateDeclForFFIExt(ctx)

        return

    def generateImplStructCtor(self, ctx):
        class_name = ctx.flat_class_name
        method_name = ctx.method_name_rewrite

        ctx.CP.AP('body', ctx.fn_proto_cpp)
        ctx.CP.AP('body', "impl /*struct*/ %s {" % (class_name))
        ctx.CP.AP('body', "  pub fn %s<T: %s_%s>(value: T) -> %s {"
                  % (method_name, class_name, method_name, class_name))
        ctx.CP.AP('body', "    let rsthis = value.%s();" % (method_name))
        ctx.CP.AP('body', "    return rsthis;")
        ctx.CP.AP('body', "    // return 1;")
        ctx.CP.AP('body', "  }")
        ctx.CP.AP('body', "}\n")
        return

    def generateImplStructMethod(self, ctx):
        class_name = ctx.flat_class_name
        method_name = ctx.method_name_rewrite
        self_code_proto = ctx.static_self_struct
        self_code_call = ctx.static_self_call

        ctx.CP.AP('body', ctx.fn_proto_cpp)
        ctx.CP.AP('body', "impl /*struct*/ %s {" % (class_name))
        ctx.CP.AP('body', "  pub fn %s<RetType, T: %s_%s<RetType>>(%s overload_args: T) -> RetType {"
                   % (method_name, class_name, method_name, self_code_proto))
        ctx.CP.AP('body', "    return overload_args.%s(%s);" % (method_name, self_code_call))
        ctx.CP.AP('body', "    // return 1;")
        ctx.CP.AP('body', "  }")
        ctx.CP.AP('body', "}\n")
        return

    def generateImplTraitCtor(self, ctx):
        method_cursor = ctx.cursor
        mangled_name = ctx.mangled_name
        class_name = ctx.flat_class_name
        method_name = ctx.method_name_rewrite
        trait_params = ctx.params_rs
        call_params = ctx.params_call

        ctx.CP.AP('body', ctx.fn_proto_cpp)
        ctx.CP.AP('body', "impl<'a> /*trait*/ %s_%s for (%s) {" % (class_name, method_name, trait_params))
        ctx.CP.AP('body', "  fn %s(self) -> %s {" % (method_name, class_name))
        ctx.CP.AP('body', "    // let qthis: *mut c_void = unsafe{calloc(1, %s)};" % (ctx.ctysz))
        ctx.CP.AP('body', "    // unsafe{%s()};" % (mangled_name))
        ctx.CP.AP('body', "    let ctysz: c_int = unsafe{%s_Class_Size()};" % (ctx.flat_class_name))
        ctx.CP.AP('body', "    let qthis_ph: u64 = unsafe{calloc(1, ctysz as usize)} as u64;")
        self.generateArgConvExprs(class_name, method_name, method_cursor, ctx)
        ctx.CP.AP('body', "    let qthis: u64 = unsafe {C%s(%s)};" % (mangled_name, call_params))
        # ctx.CP.AP('body', "    let qthis: u64 = qthis_ph;")
        if ctx.has_base:
            # TODO 如果父类再有父类呢，这个初始化不对，需要更强的生成函数
            ctx.CP.AP('body', "    let rsthis = %s{qbase: %s::inheritFrom(qthis), qclsinst: qthis, ..Default::default()};" %
                      (class_name, ctx.base_class_name))
        else:
            ctx.CP.AP('body', "    let rsthis = %s{qclsinst: qthis, ..Default::default()};" % (class_name))
        ctx.CP.AP('body', "    return rsthis;")
        ctx.CP.AP('body', "    // return 1;")
        ctx.CP.AP('body', "  }")
        ctx.CP.AP('body', "}\n")

        return

    def generateImplTraitMethod(self, ctx):
        class_name = ctx.flat_class_name
        method_cursor = cursor = ctx.cursor
        method_name = ctx.method_name_rewrite

        has_return = ctx.has_return
        return_piece_code_return = ''
        return_type_name_rs = '()'
        if has_return:
            return_type_name_rs = self.generateReturnForImplTraitT0(ctx)
            return_piece_code_return = 'let mut ret ='

        self_code_proto = ctx.static_self_trait
        trait_params = ctx.params_rs
        call_params = ctx.params_call

        mangled_name = ctx.mangled_name
        ctx.CP.AP('body', ctx.fn_proto_cpp)
        ctx.CP.AP('body', "impl<'a> /*trait*/ %s_%s<%s> for (%s) {" %
                  (class_name, method_name, return_type_name_rs, trait_params))
        ctx.CP.AP('body', "  fn %s(self %s) -> %s {" %
                  (method_name, self_code_proto, return_type_name_rs))
        ctx.CP.AP('body', "    // let qthis: *mut c_void = unsafe{calloc(1, %s)};" % (ctx.ctysz))
        ctx.CP.AP('body', "    // unsafe{%s()};" % (mangled_name))
        self.generateArgConvExprs(class_name, method_name, method_cursor, ctx)
        if ctx.isinline:
            ctx.CP.AP('body', "    %s unsafe {C%s(%s)};" % (return_piece_code_return, mangled_name, call_params))
        else:
            ctx.CP.AP('body', "    %s unsafe {C%s(%s)};" % (return_piece_code_return, mangled_name, call_params))

        if has_return: self.generateReturnForImplTrait(ctx)
        ctx.CP.AP('body', "    // return 1;")
        ctx.CP.AP('body', "  }")
        ctx.CP.AP('body', "}\n")

        # case for return qt object
        if has_return:
            self.generateUseForRust(ctx, ctx.ret_type, ctx.cursor)

        return

    def generateMethodDeclTrait(self, ctx):
        class_name = ctx.flat_class_name
        method_name = ctx.method_name_rewrite

        self_code_proto = ctx.static_self_trait

        ### trait
        if ctx.ctor is True:
            ctx.CP.AP('body', "pub trait %s_%s {" % (class_name, method_name))
            ctx.CP.AP('body', "  fn %s(self) -> %s;" % (method_name, class_name))
        else:
            ctx.CP.AP('body', "pub trait %s_%s<RetType> {" % (class_name, method_name))
            ctx.CP.AP('body', "  fn %s(self %s) -> RetType;" %
                       (method_name, self_code_proto))
        ctx.CP.AP('body', "}\n")
        return

    def generateReturnForImplTraitT0(self, ctx):
        ret_type = self.tyconv.TypeToActual(ctx.cursor.result_type)
        cret_type = self.tyconv.TypeToCanonical(ret_type)
        cret_type = self.tyconv.TypeToActual(cret_type)
        cret_type = self.tyconv.TypeToCanonical(cret_type)

        rety_name = '()'
        known_record = cret_type.spelling in self.gctx.classes
        skip_record = self.check_skip_class(cret_type.get_declaration())
        if ret_type.kind == clidx.TypeKind.RECORD and not known_record:
            rety_name = 'u64'
        elif cret_type.spelling in self.gctx.classes and skip_record:
            rety_name = 'u64'
        elif ret_type.kind == clidx.TypeKind.RECORD and known_record and not skip_record:
            rety_name = ctx.ret_type_name_rs
        elif ret_type.kind == clidx.TypeKind.POINTER and \
             'char'.upper() in str(self.tyconv.TypeToActual(ret_type.get_pointee()).kind):
            rety_name = 'String'
        elif ret_type.kind == clidx.TypeKind.POINTER and \
             ret_type.get_pointee().kind == clidx.TypeKind.RECORD:
            known_record = self.tyconv.TypeToActual(ret_type.get_pointee()).spelling in self.gctx.classes
            if known_record:
                rety_name = ctx.ret_type_name_rs
            else:
                rety_name = 'u64'
        elif 'QFunctionPointer' == ctx.ret_type_name_rs or 'EasingFunction' == ctx.ret_type_name_rs:
            rety_name = 'u64'
        else:
            if 'char' in ret_type.spelling and ret_type.kind == clidx.TypeKind.POINTER:
                print(871320921, ret_type.spelling, ctx.cursor.spelling,
                      'char'.upper() in str(ret_type.get_pointee().kind),
                      'char'.upper() in str(self.tyconv.TypeToActual(ret_type.get_pointee()).kind),
                      ret_type.get_pointee().kind
                )
            rety_name = ctx.ret_type_name_rs

        return rety_name

    def generateReturnForImplTrait(self, ctx):
        ret_type = self.tyconv.TypeToActual(ctx.cursor.result_type)
        cret_type = self.tyconv.TypeToCanonical(ret_type)
        cret_type = self.tyconv.TypeToActual(cret_type)
        cret_type = self.tyconv.TypeToCanonical(cret_type)

        known_record = cret_type.spelling in self.gctx.classes
        skip_record = self.check_skip_class(cret_type.get_declaration())
        if ret_type.kind == clidx.TypeKind.RECORD and not known_record:
            ctx.CP.AP('body', "    return ret as %s; // 5" % ('u64'))
        elif cret_type.spelling in self.gctx.classes and skip_record:
            ctx.CP.AP('body', "    return ret as %s; // 2" % ('u64'))
        elif ret_type.kind == clidx.TypeKind.RECORD and known_record and not skip_record:
            ctx.CP.AP('body', "    let mut ret1 = %s::inheritFrom(ret as u64);" % (ctx.ret_type_name_rs))
            ctx.CP.AP('body', "    return ret1;")
        elif ret_type.kind == clidx.TypeKind.POINTER and \
             'char'.upper() in str(self.tyconv.TypeToActual(ret_type.get_pointee()).kind):
            ctx.CP.AP('body', "    let slen = unsafe {strlen(ret as *const i8)} as usize;")
            ctx.CP.AP('body', "    return unsafe{String::from_raw_parts(ret as *mut u8, slen, slen+1)};")
        elif ret_type.kind == clidx.TypeKind.POINTER and \
             ret_type.get_pointee().kind == clidx.TypeKind.RECORD:
            known_record = self.tyconv.TypeToActual(ret_type.get_pointee()).spelling in self.gctx.classes
            if known_record:
                ctx.CP.AP('body', "    let mut ret1 = %s::inheritFrom(ret as u64);" % (ctx.ret_type_name_rs))
                ctx.CP.AP('body', "    return ret1;")
            else:
                ctx.CP.AP('body', "    return ret as %s; // 4" % ('u64'))
        elif 'QFunctionPointer' == ctx.ret_type_name_rs or 'EasingFunction' == ctx.ret_type_name_rs:
            ctx.CP.AP('body', "    return ret as %s; // 3" % ('u64'))
        else:
            if 'char' in ret_type.spelling and ret_type.kind == clidx.TypeKind.POINTER:
                print(871320921, ret_type.spelling, ctx.cursor.spelling,
                      'char'.upper() in str(ret_type.get_pointee().kind),
                      'char'.upper() in str(self.tyconv.TypeToActual(ret_type.get_pointee()).kind),
                      ret_type.get_pointee().kind
                )
            ctx.CP.AP('body', "    return ret as %s; // 1" % (ctx.ret_type_name_rs))

        return

    def generateArgConvExprs(self, class_name, method_name, method_cursor, ctx):
        argc = 0
        for arg in method_cursor.get_arguments(): argc += 1

        def isvec(tyname): return 'Vec<' in tyname

        def isrstr(tyname): return 'String' in tyname.split(' ')

        def hasdarg(arg): return self.gutil.hasDefaultArg(arg)

        def dargsrc(arg): return self.gutil.defaultArgSrc(arg)

        def evaldarg(arg):
            dva = False
            tks = list(arg.get_tokens())
            for idx, (tk) in enumerate(tks):
                if tk.kind == clidx.TokenKind.PUNCTUATION and tk.spelling == '=':
                    dva = True
                    continue
                if tk.kind == clidx.TokenKind.PUNCTUATION and tk.spelling == ')':
                    break
                if dva is True:
                    tkc = tk.cursor
                    if tkc.kind == clidx.CursorKind.CHARACTER_LITERAL:
                        return "%s as i8" % (tk.spelling)
                    elif tkc.kind == clidx.CursorKind.INTEGER_LITERAL:
                        aty = self.tyconv.TypeToCanonical(self.tyconv.TypeToActual(arg.type))
                        srctype = self.tyconv.TypeCXX2Rust(arg.type, arg)
                        if isrstr(srctype):
                            return tk.spelling + ' as *const u8'
                        elif isvec(srctype):
                            if aty.kind == clidx.TypeKind.INT:
                                return tk.spelling + ' as *const i32'
                            elif aty.kind == clidx.TypeKind.LONGLONG:
                                return tk.spelling + ' as *const i64'
                            elif aty.kind == clidx.TypeKind.DOUBLE:
                                return tk.spelling + ' as *const f64'
                            return tk.spelling + ' as *const i8'
                        elif arg.type.spelling.endswith('void *'):
                            return tk.spelling + ' as *mut c_void'
                        elif aty.kind == clidx.TypeKind.DOUBLE:
                            return tk.spelling + ' as f64'
                        else:
                            return tk.spelling
                    elif tkc.kind == clidx.CursorKind.FLOATING_LITERAL:
                        return tk.spelling.strip('f')
                    elif tkc.kind == clidx.CursorKind.CXX_BOOL_LITERAL_EXPR:
                        return tk.spelling + ' as i8'  # maybe change to as u8
                    elif tkc.kind == clidx.CursorKind.UNARY_OPERATOR:
                        return '%s%s' % (tk.spelling, tks[idx + 1].spelling)
                    elif tkc.kind == clidx.CursorKind.TYPE_REF:
                        aty = self.tyconv.TypeToCanonical(self.tyconv.TypeToActual(arg.type))
                        if aty.kind == clidx.TypeKind.INT:
                            return '0 as i32'
                        if tk.spelling == 'QLatin1Char':
                            return '%s::new((0 as i8)).qclsinst' % (tk.spelling)
                        return '%s::new(()).qclsinst' % (tk.spelling)
                    elif tkc.kind == clidx.CursorKind.NAMESPACE_REF:
                        aty = self.tyconv.TypeToCanonical(self.tyconv.TypeToActual(arg.type))
                        if aty.kind == clidx.TypeKind.RECORD:
                            return '%s::new(()).qclsinst' % (aty.spelling)
                        return '0 as i32'
                    elif tkc.kind == clidx.CursorKind.DECL_REF_EXPR and tk.spelling.startswith('ApplicationFlags'):
                        return '0 as i32'
                    elif tkc.kind == clidx.CursorKind.DECL_REF_EXPR and tk.spelling.startswith('SO_'):
                        return '0 as i32'
                    elif tkc.kind == clidx.CursorKind.DECL_REF_EXPR and tk.spelling.startswith('SH_'):
                        return '0 as i32'
                    elif tkc.kind == clidx.CursorKind.DECL_REF_EXPR and tk.spelling == 'Type':
                        return '0 as i32'
                    elif tkc.kind == clidx.CursorKind.PARM_DECL and tk.spelling.startswith('GL_'):
                        return '0 as u32'
                    elif tkc.kind == clidx.CursorKind.CXX_METHOD and tk.spelling == 'ULONG_MAX':
                        return 'i32::max_value() as u64'
                    else:
                        print(55555, ctx.method_name, arg.displayname, arg.kind, dargsrc(arg))
                        print(5555, tk.kind, tk.spelling.strip("'"), tk.cursor.kind)
                        # raise 'wtf'
                    break
            return ''

        for idx, (arg) in enumerate(method_cursor.get_arguments()):
            srctype = self.tyconv.TypeCXX2Rust(arg.type, arg)
            astype = self.tyconv.TypeCXX2RustExtern(arg.type, arg)
            astype = ' as %s' % (astype)
            asptr = ''
            if self.tyconv.IsPointer(arg.type) and self.tyconv.IsCharType(arg.type.spelling):
                asptr = '.as_ptr()'
            elif isvec(srctype): asptr = '.as_ptr()'
            elif isrstr(srctype): asptr = '.as_ptr()'

            qclsinst = ''
            can_name = self.tyconv.TypeCanName(arg.type)
            if self.is_qt_class(can_name): qclsinst = '.qclsinst'
            selfn = 'self' if argc == 1 else 'self.%s' % (idx)  # fix shit rust tuple index
            if hasdarg(arg):
                ctx.CP.AP('body', "    let arg%s = (if %s.is_none() {%s} else {%s.unwrap()%s%s}) %s;"
                          % (idx, selfn, evaldarg(arg), selfn, qclsinst, asptr, astype))
            else:
                ctx.CP.AP('body', "    let arg%s = %s%s%s %s;" % (idx, selfn, qclsinst, asptr, astype))
            # if argc == 1:  # fix shit rust tuple index
            #    ctx.CP.AP('body', "    let arg%s = self%s%s %s;" % (idx, qclsinst, asptr, astype))
            # else:
            #    ctx.CP.AP('body', "    let arg%s = self.%s%s%s %s;" % (idx, idx, qclsinst, asptr, astype))
        return

    # @return []
    def generateParams(self, class_name, method_name, method_cursor):
        idx = 0
        argv = []

        for arg in method_cursor.get_arguments():
            idx += 1
            # print('%s, %s, ty:%s, kindty:%s' % (method_name, arg.displayname, arg.type.spelling, arg.kind))
            # print('arg type kind: %s, %s' % (arg.type.kind, arg.type.get_declaration()))

            type_name = self.resolve_swig_type_name(class_name, arg.type)
            type_name2 = self.hotfix_typename_ifenum_asint(class_name, arg, arg.type)
            type_name = type_name2 if type_name2 is not None else type_name

            arg_name = 'arg%s' % idx if arg.displayname == '' else arg.displayname
            # try fix void (*)(void *) 函数指针
            # 实际上swig不需要给定名字，只需要类型即可。
            if arg.type.kind == clang.cindex.TypeKind.POINTER and "(*)" in type_name:
                argelem = "%s" % (type_name.replace('(*)', '(*%s)' % arg_name))
            else:
                argelem = "%s %s" % (type_name, arg_name)
            argv.append(argelem)

        return argv

    # @return []
    def generateParamsRaw(self, class_name, method_name, method_cursor):
        argv = []
        for arg in method_cursor.get_arguments():
            argelem = "%s %s" % (arg.type.spelling, arg.displayname)
            argv.append(argelem)
        return argv

    # @return []
    def generateParamsForCall(self, class_name, method_name, method_cursor):
        idx = 0
        argv = []

        for arg in method_cursor.get_arguments():
            idx += 1
            # print('%s, %s, ty:%s, kindty:%s' % (method_name, arg.displayname, arg.type.spelling, arg.kind))
            # print('arg type kind: %s, %s' % (arg.type.kind, arg.type.get_declaration()))

            type_name = self.resolve_swig_type_name(class_name, arg.type)
            type_name2 = self.hotfix_typename_ifenum_asint(class_name, arg, arg.type)
            type_name = type_name2 if type_name2 is not None else type_name

            type_name_extern = self.tyconv.TypeCXX2RustExtern(arg.type, arg)
            arg_name = 'arg%s' % idx if arg.displayname == '' else arg.displayname
            argelem = "arg%s" % (idx - 1)
            argv.append(argelem)

        return argv

    # @return []
    def generateParamsForTrait(self, class_name, method_name, method_cursor, ctx):
        idx = 0
        argv = []

        for arg in method_cursor.get_arguments():
            idx += 1
            # print('%s, %s, ty:%s, kindty:%s' % (method_name, arg.displayname, arg.type.spelling, arg.kind))
            # print('arg type kind: %s, %s' % (arg.type.kind, arg.type.get_declaration()))

            if self.check_skip_param(arg, method_name) is False:
                self.generateUseForRust(ctx, arg.type, arg)

            type_name = self.tyconv.TypeCXX2Rust(arg.type, arg, inty=True)
            if type_name.startswith('&'): type_name = type_name.replace('&', "&'a ")

            if self.gutil.hasDefaultArg(arg):
                argelem = "Option<%s>" % (type_name)
            else:
                argelem = "%s" % (type_name)
            argv.append(argelem)

        return argv

    # @return []
    def generateParamsForExtern(self, class_name, method_name, method_cursor, ctx):
        idx = 0
        argv = []

        if method_cursor.kind == clang.cindex.CursorKind.CONSTRUCTOR:
            # argv.append('qthis: *mut c_void')
            pass

        for arg in method_cursor.get_arguments():
            idx += 1
            # print('%s, %s, ty:%s, kindty:%s' % (method_name, arg.displayname, arg.type.spelling, arg.kind))
            # print('arg type kind: %s, %s' % (arg.type.kind, arg.type.get_declaration()))

            if self.check_skip_param(arg, method_name) is False:
                self.generateUseForRust(ctx, arg.type, arg)
            type_name = self.tyconv.TypeCXX2RustExtern(arg.type, arg)

            arg_name = 'arg%s' % idx if arg.displayname == '' else arg.displayname
            argelem = "arg%s: %s" % (idx - 1, type_name)
            argv.append(argelem)

        return argv

    def generateReturnForImplStruct(self, class_name, method_cursor, ctx):
        cursor = ctx.cursor

        return_type = cursor.result_type
        return_real_type = self.real_type_name(return_type)

        return_type_name = return_type.spelling
        if cursor.kind == clang.cindex.CursorKind.CONSTRUCTOR or \
           cursor.kind == clang.cindex.CursorKind.DESTRUCTOR:
            pass
        else:
            return_type_name = self.resolve_swig_type_name(class_name, return_type)
            return_type_name2 = self.hotfix_typename_ifenum_asint(class_name, method_cursor, return_type)
            return_type_name = return_type_name2 if return_type_name2 is not None else return_type_name

        has_return = ctx.has_return

        return has_return, return_type_name

    def generateDeclForFFIExt(self, ctx):
        cursor = ctx.cursor
        has_return = ctx.has_return
        # calc ext type name
        return_type_name = self.tyconv.TypeCXX2RustExtern(ctx.ret_type, cursor, True)

        mangled_name = ctx.mangled_name
        return_piece_proto = ''
        if cursor.result_type.kind != clang.cindex.TypeKind.VOID and has_return:
            return_piece_proto = ' -> %s' % (return_type_name)
        extargs = ctx.params_ext
        if ctx.ctor: return_piece_proto = ' -> %s' % ('u64')

        if ctx.isinline:
            ctx.CP.AP('ext', "  fn C%s(%s)%s;" % (mangled_name, extargs, return_piece_proto))
        else:
            ctx.CP.AP('ext', "  fn C%s(%s)%s;" % (mangled_name, extargs, return_piece_proto))

        return has_return, return_type_name

    def methodHasReturn(self, ctx):
        method_cursor = cursor = ctx.cursor
        class_name = ctx.flat_class_name

        return_type = cursor.result_type

        return_type_name = return_type.spelling
        if ctx.ctor or ctx.dtor: pass
        else:
            return_type_name = self.resolve_swig_type_name(class_name, return_type)
            return_type_name2 = self.hotfix_typename_ifenum_asint(class_name, method_cursor, return_type)
            return_type_name = return_type_name2 if return_type_name2 is not None else return_type_name

        has_return = True
        if return_type_name == 'void': has_return = False
        return has_return

    # TODO 使用use A::*简化use的生成，精确度 到头文件l级别，非struct级别
    def generateUseForRust(self, ctx, aty, cursor):
        class_name = ctx.flat_class_name
        # type_name = self.resolve_swig_type_name(class_name, arg.type)
        # type_name2 = self.hotfix_typename_ifenum_asint(class_name, arg, arg.type)
        # type_name = type_name2 if type_name2 is not None else type_name

        def genuseimpl(ctx, cursor, ncursor, seg):
            seg_code_file = self.gutil.get_code_file(ncursor)
            cur_code_file = self.gutil.get_code_file(cursor)
            seg_mod = self.gutil.get_decl_mod(ncursor)
            cur_mod = self.gutil.get_decl_mod(cursor)

            if seg_mod != cur_mod:  # 引用的类不在当前mod中
                ctx.CP.APU('use', "use super::super::%s::%s::*; // 771" % (seg_mod, seg_code_file))
            else:
                if seg_code_file == cur_code_file:
                    ctx.CP.APU('use', "// use super::%s::%s; // 773" % (seg_code_file, seg))
                else:
                    ctx.CP.APU('use', "use super::%s::*; // 773" % (seg_code_file))
            return

        type_name = self.tyconv.TypeCXX2Rust(aty, cursor)
        if type_name.startswith('&'): type_name = type_name.replace('&', "&'a ")
        if self.is_qt_class(type_name):
            seg = self.get_qt_class(type_name)
            # 不但不能是当前类，并且也不能是当前文件中的类
            if seg != class_name:
                if seg in self.gctx.classes:
                    ncursor = self.gctx.classes[seg]
                    genuseimpl(ctx, cursor, ncursor, seg)
                else:
                    # 不在类列表中的引用不了，如果有使用的地方，还是再找原因比较好
                    # 原因找到了，主要是模板类的问题啊
                    ctx.CP.APU('use', "// use super::%s::*; // 775" % (seg.lower()))
                    clstp = self.gutil.isTempInstClass(aty.get_declaration())
                    if clstp is not None:
                        tcls = self.get_instantiated_class(aty.get_declaration())
                        if tcls is None:
                            print(seg, clstp, type_name)
                            raise 'wtf'
                        if not self.check_skip_class(tcls):
                            genuseimpl(ctx, cursor, tcls, seg)
        return

    def dedup_return_const_diff_method(self, methods):
        dupremove = []
        for mtop in methods:
            postop = mtop.find('Q')
            for msub in methods:
                if mtop == msub: continue
                possub = msub.find('Q')
                if mtop[postop:] != msub[possub:]: continue
                if postop > possub: dupremove.append(mtop)
                else: dupremove.append(msub)
        return dupremove

    def reform_return_type_name(self, retname):
        lst = retname.split(' ')
        for elem in lst:
            if self.is_qt_class(elem): return elem
            if elem == 'String': return elem
        return retname

    def fix_conflict_method_name(self, method_name):
        mthname = method_name
        fixmthname = mthname
        if mthname in ['match', 'type', 'move']:  # , 'select']:
            fixmthname = mthname + '_'
        return fixmthname

    def is_conflict_method_name(self, method_name):
        if method_name in ['match', 'type', 'move']:  # , 'select']:
            return True
        return False

    # @return True | False
    def check_skip_params(self, cursor):
        method_name = cursor.spelling
        for arg in cursor.get_arguments():
            if self.check_skip_param(arg, method_name) is True: return True
        return False

    def check_skip_param(self, arg, method_name):
        if True:
            type_name = arg.type.spelling
            type_name_segs = type_name.split(' ')
            if 'const' in type_name_segs: type_name_segs.remove('const')
            if '*' in type_name_segs: type_name_segs.remove('*')
            if '&' in type_name_segs: type_name_segs.remove('&')
            type_name = type_name_segs[0]

            # Fix && move语义参数方法，
            if '&&' in type_name: return True
            if arg.type.kind == clang.cindex.TypeKind.RVALUEREFERENCE: return True
            if 'QPrivate' in type_name: return True
            if 'Private' in type_name: return True
            # if 'QAbstract' in type_name: return True
            if 'QLatin1String' == type_name: return True
            if 'QLatin1Char' == type_name: return True
            if 'QStringRef' in type_name: return True
            if 'QStringDataPtr' in type_name: return True
            if 'QByteArrayDataPtr' in type_name: return True
            if 'QModelIndexList' in type_name: return True
            if 'QXmlStreamNamespaceDeclarations' in type_name: return True
            if 'QGenericArgument' in type_name: return True
            if 'QJson' in type_name: return True
            # if 'QWidget' in type_name: return True
            if 'QTextEngine' in type_name: return True
            # if 'QAction' in type_name: return True
            if 'QPlatformPixmap' in type_name: return True
            if 'QPlatformScreen' in type_name: return True
            if 'QPlatformMenu' in type_name: return True
            if 'QFileDialogArgs' in type_name: return True
            if 'FILE' in type_name: return True
            if 'sockaddr' in type_name: return True
            if 'QQmlCompiledData' in type_name: return True
            if 'QQmlContextData' in type_name: return True
            if 'QQuickCloseEvent' in type_name: return True
            if 'QQmlV4Function' in type_name: return True

            if type_name[0:1] == 'Q' and '::' in type_name: return True  # 有可能是类内类，像QMetaObject::Connection
            if '<' in type_name: return True  # 模板类参数
            # void directoryChanged(const QString & path, QFileSystemWatcher::QPrivateSignal arg0);
            # 这个不准确，会把QCoreApplication(int &, char**, int)也过滤掉了
            if method_name == 'QCoreApplication': pass
            else:
                if arg.displayname == '' and type_name == 'int':
                    # print(555, 'whyyyyyyyyyyyyyy', method_name, arg.type.spelling)
                    # return True  # 过滤的不对，前边的已经过滤掉。
                    pass

            #### more
            can_type = self.tyconv.TypeToCanonical(arg.type)
            if can_type.kind == clang.cindex.TypeKind.FUNCTIONPROTO: return True
            # if method_name == 'fromRotationMatrix':
            if can_type.kind == clang.cindex.TypeKind.RECORD:
                decl = can_type.get_declaration()
                for token in decl.get_tokens():
                    # print(555, token.spelling)
                    if token.spelling == 'template': return True
                    break
                # print(555, can_type.kind, method_name, decl.kind, decl.spelling,
                      #decl.get_num_template_arguments(),
                      #)
                # exit(0)

        return False

    # @return True | False
    def check_skip_method(self, cursor):
        # shitfix begin
        # shitfix end

        if True: return self.gfilter.skipMethod(cursor)
        return False

    def check_skip_class(self, class_cursor):
        # shitfix begin
        class_name = class_cursor.spelling
        if class_name in ['QSignalMapper']: return True
        # shitfix end

        if True: return self.gfilter.skipClass(class_cursor)
        return False

    # def hotfix_typename_ifenum_asint(self, class_name, arg):
    def hotfix_typename_ifenum_asint(self, class_name, token_cursor, atype):
        type_name = self.resolve_swig_type_name(class_name, atype)
        # if type_name not in ('int', 'int *', 'const int &'): return None
        type_name_segs = type_name.split(' ')
        if 'int' not in type_name_segs: return None

        tokens = []
        for token in token_cursor.get_tokens():
            tokens.append(token.spelling)
            tkcursor = token.cursor

        # 为什么tokens是空呢，是不能识别的？
        if len(tokens) == 0: return None
        # TODO 全部使用replace方式，而不是这种每个符号的处理
        while tokens[0] in ['const', 'inline']:
            tokens = tokens[1:]

        tydecl = atype.get_declaration()
        tyloc = atype.get_declaration().location

        firstch = tokens[0][0:1]
        if firstch.upper() == firstch and firstch != 'Q':
            if tydecl is not None and tydecl.semantic_parent is not None \
               and self.gutil.isqtloc(tydecl.semantic_parent):
                print('Warning fix enum-as-int:', type_name, '=> %s::' % class_name, tokens[0])
                return '%s::%s' % (class_name, tokens[0])

        return None

    def real_type_name(self, atype):
        type_name = atype.spelling

        if atype.kind == clang.cindex.TypeKind.TYPEDEF:
            type_name = atype.get_declaration().underlying_typedef_type.spelling
            if type_name.startswith('QFlags<'):
                type_name = type_name[7:len(type_name) - 1]

        return type_name

    # @return str
    def resolve_swig_type_name(self, class_name, atype):
        type_name = atype.spelling
        if type_name in ['QFunctionPointer', 'CategoryFilter',
                         'EasingFunction']:
            type_bclass = atype.get_declaration().semantic_parent
            # 全局定义的，不需要前缀
            if type_bclass.kind == clang.cindex.CursorKind.TRANSLATION_UNIT: pass
            else: type_name = '%s::%s' % (type_bclass.spelling, type_name)
        else:
            type_name = self.real_type_name(atype)

        return type_name

    def get_cursor_tokens(self, cursor):
        tokens = []
        for token in cursor.get_tokens():
            tokens.append(token.spelling)
        return ' '.join(tokens)

    def genpass_write_codes(self):
        for key in self.gctx.codes:
            cp = self.gctx.codes[key]
            code = cp.exportCode(self.class_blocks)

            mod = self.gctx.get_decl_mod_by_path(key)
            fname = self.gctx.get_code_file_by_path(key)
            if mod not in ['core', 'gui', 'widgets', 'network', 'dbus', 'qml', 'quick']:
                print('Omit unknown mod code...:', mod, fname, key)
                continue

            self.write_code(mod, fname, code)
            # self.write_file(fpath, code)

        # class mod define
        # self.write_modrs(module, self.MP.exportCode(['main']))
        for mod in self.modrss:
            cp = self.modrss[mod]
            code = cp.exportCode(['main'])
            lines = cp.totalLine()
            print('write mod.rs:', mod, len(code), lines)
            self.write_modrs(mod, code)
        return

    def write_code(self, mod, fname, code):
        # mod = 'core'
        # fpath = "src/core/%s.rs" % (fname)
        fpath = "src/%s/%s.rs" % (mod, fname)
        self.write_file(fpath, code)
        return

    # TODO dir is exists
    def write_file(self, fpath, code):
        f = os.open(fpath, os.O_CREAT | os.O_TRUNC | os.O_RDWR)
        os.write(f, code)
        os.close(f)

        return

    def write_modrs(self, mod, code):
        fpath = "src/%s/mod.rs" % (mod)
        self.write_file(fpath, code)
        return
    pass

