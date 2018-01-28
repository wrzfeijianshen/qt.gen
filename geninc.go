package main

import (
	"fmt"
	"gopp"
	"io/ioutil"
	"log"
	"path/filepath"
	"strings"

	"github.com/go-clang/v3.9/clang"
)

type GenerateInline struct {
	// TODO move to base
	filter   GenFilter
	tyconver *TypeConvertGo
	mangler  GenMangler

	methods   []clang.Cursor
	cp        *CodePager
	argDesc   []string
	paramDesc []string

	pureVirtual bool
}

func NewGenerateInline() *GenerateInline {
	this := &GenerateInline{}
	this.filter = &GenFilterInc{}
	this.mangler = NewIncMangler()
	this.tyconver = NewTypeConvertGo()

	this.cp = NewCodePager()
	blocks := []string{"header", "main", "use", "ext", "body"}
	for _, block := range blocks {
		this.cp.AddPointer(block)
	}

	return this
}

func (this *GenerateInline) genClass(cursor, parent clang.Cursor) {
	if false {
		log.Println(cursor.Spelling(), cursor.Kind().String(), cursor.DisplayName())
	}
	file, line, col, _ := cursor.Location().FileLocation()
	if false {
		log.Printf("%s:%d:%d @%s\n", file.Name(), line, col, file.Time().String())
	}

	this.pureVirtual = false
	this.genHeader(cursor, parent)
	this.walkClass(cursor, parent)
	this.genProtectedCallbacks(cursor, parent)
	this.genProxyClass(cursor, parent)
	this.genMethods(cursor, parent)
	this.final(cursor, parent)
}

func (this *GenerateInline) final(cursor, parent clang.Cursor) {
	// log.Println(this.cp.ExportAll())
	this.saveCode(cursor, parent)

	this.cp = NewCodePager()
}
func (this *GenerateInline) saveCode(cursor, parent clang.Cursor) {
	// qtx{yyy}, only yyy
	file, line, col, _ := cursor.Location().FileLocation()
	if false {
		log.Printf("%s:%d:%d @%s\n", file.Name(), line, col, file.Time().String())
	}
	modname := strings.ToLower(filepath.Base(filepath.Dir(file.Name())))[2:]
	savefile := fmt.Sprintf("src/%s/%s.cxx", modname, strings.ToLower(cursor.Spelling()))

	ioutil.WriteFile(savefile, []byte(this.cp.ExportAll()), 0644)
}

func (this *GenerateInline) genHeader(cursor, parent clang.Cursor) {
	file, line, col, _ := cursor.Location().FileLocation()
	if false {
		log.Printf("%s:%d:%d @%s\n", file.Name(), line, col, file.Time().String())
	}
	this.cp.APf("header", "// %s", file.Name())
	hbname := filepath.Base(file.Name())
	if strings.HasSuffix(hbname, "_impl.h") {
		this.cp.APf("header", "#include <%s.h>", hbname[:len(hbname)-7])
	} else {
		this.cp.APf("header", "#include <%s>", filepath.Base(file.Name()))
	}
	fullModname := filepath.Base(filepath.Dir(file.Name()))
	this.cp.APf("header", "#include <%s>", fullModname)
	this.cp.APf("header", "")
}

func (this *GenerateInline) walkClass(cursor, parent clang.Cursor) {
	pureVirt := false
	methods := make([]clang.Cursor, 0)

	// pcursor := cursor
	cursor.Visit(func(cursor, parent clang.Cursor) clang.ChildVisitResult {
		switch cursor.Kind() {
		case clang.Cursor_Constructor:
			pureVirt = pureVirt || cursor.CXXMethod_IsPureVirtual()
			fallthrough
		case clang.Cursor_Destructor:
			fallthrough
		case clang.Cursor_CXXMethod:
			pureVirt = pureVirt || cursor.CXXMethod_IsPureVirtual()
			if !this.filter.skipMethod(cursor, parent) {
				methods = append(methods, cursor)
			} else {
				// log.Println("filtered:", cursor.Spelling())
			}
		case clang.Cursor_UnexposedDecl:
			// log.Println(cursor.Spelling(), cursor.Kind().String(), cursor.DisplayName())
			file, line, col, _ := cursor.Location().FileLocation()
			if false {
				log.Println(file.Name(), line, col, file.Time())
			}
		default:
			if false {
				log.Println(cursor.Spelling(), cursor.Kind().String(), cursor.DisplayName())
			}
		}
		return clang.ChildVisit_Continue
	})

	this.pureVirtual = pureVirt
	if !pureVirt {
		this.pureVirtual = is_pure_virtual_class(cursor)
	}
	this.cp.APf("header", "// %s is pure virtual: %v", cursor.Spelling(), pureVirt)
	this.methods = methods
}

func (this *GenerateInline) genProtectedCallbacks(cursor, parent clang.Cursor) {
	log.Println("process class:", len(this.methods), cursor.Spelling())
	for _, cursor := range this.methods {
		parent := cursor.SemanticParent()
		// log.Println(cursor.Kind().String(), cursor.DisplayName())

		if cursor.AccessSpecifier() == clang.AccessSpecifier_Protected {
			this.genProtectedCallback(cursor, parent)
		}
	}

	this.cp.APf("main", "")
}

func (this *GenerateInline) genProxyClass(cursor, parent clang.Cursor) {

	if is_deleted_class(cursor) {
		return
	}

	this.cp.APf("main", "class My%s : public %s {", cursor.Spelling(), cursor.Type().Spelling())
	this.cp.APf("main", "public:")

	for _, mcs := range this.methods {
		if mcs.Kind() == clang.Cursor_Constructor {
			this.genArgs(mcs, cursor)
			argStr := strings.Join(this.argDesc, ", ")
			this.genParams(mcs, cursor)
			paramStr := strings.Join(this.paramDesc, ", ")
			if len(argStr) > 0 {
				// argStr = ", " + argStr
			}
			this.cp.APf("main", "My%s(%s) : %s(%s) {}", mcs.Spelling(),
				argStr, cursor.Type().Spelling(), paramStr)
			continue
		}
		if mcs.AccessSpecifier() != clang.AccessSpecifier_Protected {
			continue
		}
		this.cp.APf("main", "// %s %s", mcs.ResultType().Spelling(), mcs.DisplayName())
		if mcs.Kind() == clang.Cursor_Destructor {
			continue
		}

		this.genArgs(mcs, cursor)
		argStr := strings.Join(this.argDesc, ", ")
		this.genParams(mcs, cursor)
		paramStr := strings.Join(this.paramDesc, ", ")
		if len(argStr) > 0 {
			// argStr = ", " + argStr
		}

		this.cp.APf("main", "// %s %s", mcs.ResultType().Spelling(), mcs.DisplayName())
		this.cp.APf("main", "virtual %s %s(%s) {", mcs.ResultType().Spelling(), mcs.Spelling(), argStr)
		this.cp.APf("main", "  if (callback%s != 0) {", mcs.Mangling())
		this.cp.APf("main", "  // callback%s(%s);", mcs.Mangling(), paramStr)
		this.cp.APf("main", "}}")
	}

	this.cp.APf("main", "};")
	this.cp.APf("main", "")

}

func (this *GenerateInline) genMethods(cursor, parent clang.Cursor) {
	log.Println("process class:", len(this.methods), cursor.Spelling())

	for _, cursor := range this.methods {
		parent := cursor.SemanticParent()
		// log.Println(cursor.Kind().String(), cursor.DisplayName())
		if cursor.AccessSpecifier() == clang.AccessSpecifier_Protected {
			continue
		}

		this.genMethodHeader(cursor, parent)
		switch cursor.Kind() {
		case clang.Cursor_Constructor:
			this.genCtor(cursor, parent)
		case clang.Cursor_Destructor:
			this.genDtor(cursor, parent)
		default:
			if cursor.CXXMethod_IsStatic() {
				this.genStaticMethod(cursor, parent)
			} else {
				this.genNonStaticMethod(cursor, parent)
			}
		}
	}
}

// TODO move to base
func (this *GenerateInline) genMethodHeader(cursor, parent clang.Cursor) {
	qualities := make([]string, 0)
	qualities = append(qualities, strings.Split(cursor.AccessSpecifier().Spelling(), "=")[1])
	if cursor.CXXMethod_IsStatic() {
		qualities = append(qualities, "static")
	}
	if cursor.IsFunctionInlined() {
		qualities = append(qualities, "inline")
	}
	if cursor.CXXMethod_IsPureVirtual() {
		qualities = append(qualities, "purevirtual")
	}
	if cursor.CXXMethod_IsVirtual() {
		qualities = append(qualities, "virtual")
	}
	qualities = append(qualities, cursor.Visibility().String())
	qualities = append(qualities, cursor.Availability().String())
	if len(qualities) > 0 {
		this.cp.APf("main", "// %s", strings.Join(qualities, " "))
	}

	file, lineno, _, _ := cursor.Location().FileLocation()
	this.cp.APf("main", "// %s:%d", file.Name(), lineno)
	this.cp.APf("main", "// [%d] %s %s",
		cursor.ResultType().SizeOf(), cursor.ResultType().Spelling(), cursor.DisplayName())
	this.cp.APf("main", "extern \"C\"")
}

func (this *GenerateInline) genCtor(cursor, parent clang.Cursor) {
	// log.Println(this.mangler.convTo(cursor))
	this.genArgs(cursor, parent)
	argStr := strings.Join(this.argDesc, ", ")
	this.genParams(cursor, parent)
	paramStr := strings.Join(this.paramDesc, ", ")

	pparent := parent.SemanticParent()
	log.Println(cursor.Spelling(), parent.DisplayName(),
		cursor.SemanticParent().DisplayName(), cursor.LexicalParent().DisplayName(),
		pparent.Spelling(), parent.CanonicalCursor().DisplayName())

	pureVirtRetstr := gopp.IfElseStr(this.pureVirtual, "0; //", "")

	this.cp.APf("main", "void* %s(%s) {", this.mangler.convTo(cursor), argStr)
	pxyclsp := ""
	if !is_deleted_class(parent) {
		this.cp.APf("main", "  (My%s*)(0);", parent.Spelling())
		pxyclsp = "My"
	}
	if strings.HasPrefix(pparent.Spelling(), "Qt") {
		this.cp.APf("main", "  return %s new %s%s(%s);", pureVirtRetstr, pxyclsp, parent.Spelling(), paramStr)
	} else {
		this.cp.APf("main", "  return %s new %s%s(%s);", pureVirtRetstr, pxyclsp, parent.Spelling(), paramStr)
	}

	this.cp.APf("main", "}")
}

func (this *GenerateInline) genDtor(cursor, parent clang.Cursor) {
	pparent := parent.SemanticParent()

	this.cp.APf("main", "void %s(void *this_) {", this.mangler.convTo(cursor))
	if strings.HasPrefix(pparent.Spelling(), "Qt") {
		this.cp.APf("main", "  delete (%s::%s*)(this_);", pparent.Spelling(), parent.Spelling())
	} else {
		this.cp.APf("main", "  delete (%s*)(this_);", parent.Spelling())
	}
	this.cp.APf("main", "}")
}

func (this *GenerateInline) genNonStaticMethod(cursor, parent clang.Cursor) {
	this.genArgs(cursor, parent)
	argStr := strings.Join(this.argDesc, ", ")
	this.genParams(cursor, parent)
	paramStr := strings.Join(this.paramDesc, ", ")
	if len(argStr) > 0 {
		argStr = ", " + argStr
	}

	pparent := parent.SemanticParent()
	pparentstr := ""
	if strings.HasPrefix(pparent.Spelling(), "Qt") {
		pparentstr = fmt.Sprintf("%s::", pparent.Spelling())
	}

	retstr := "void"
	retset := false
	rety := cursor.ResultType()
	cancpobj := has_copy_ctor(rety.Declaration()) || is_trivial_class(rety.Declaration())
	if rety.Kind() == clang.Type_Void {
	} else if isPrimitiveType(rety) {
		retstr = rety.Spelling()
		retset = true
	} else if rety.Kind() == clang.Type_Pointer {
		retstr = "void*"
		retset = true
	} else {
		if cancpobj {
			retstr = "void*"
		} else if rety.Kind() == clang.Type_LValueReference && TypeIsConsted(rety) {
			retstr = "void*"
		} else if rety.Kind() == clang.Type_LValueReference && !TypeIsConsted(rety) {
			retstr = "void*"
		}
	}

	this.cp.APf("main", "%s %s(void *this_%s) {", retstr, this.mangler.convTo(cursor), argStr)
	log.Println(rety.Spelling(), rety.Declaration().Spelling(), rety.IsPODType())
	if cursor.ResultType().Kind() == clang.Type_Void {
		this.cp.APf("main", "  ((%s%s*)this_)->%s(%s);", pparentstr, parent.Spelling(), cursor.Spelling(), paramStr)
	} else {
		if retset {
			this.cp.APf("main", "  return (%s)((%s%s*)this_)->%s(%s);", retstr, pparentstr, parent.Spelling(), cursor.Spelling(), paramStr)
		} else {
			autoand := gopp.IfElseStr(rety.Kind() == clang.Type_LValueReference, "auto&", "auto")
			this.cp.APf("main", "  %s rv = ((%s%s*)this_)->%s(%s);",
				autoand, pparentstr, parent.Spelling(), cursor.Spelling(), paramStr)

			if cancpobj {
				unconstystr := strings.Replace(rety.Spelling(), "const ", "", 1)
				this.cp.APf("main", "return new %s(rv);", unconstystr)
			} else if rety.Kind() == clang.Type_LValueReference && TypeIsConsted(rety) {
				unconstystr := strings.Replace(rety.PointeeType().Spelling(), "const ", "", 1)
				this.cp.APf("main", "return new %s(rv);", unconstystr)
			} else if rety.Kind() == clang.Type_LValueReference && !TypeIsConsted(rety) {
				this.cp.APf("main", "return &rv;")
			} else {
				this.cp.APf("main", "/*return rv;*/")
			}
		}
	}
	this.cp.APf("main", "}")
}

func (this *GenerateInline) genStaticMethod(cursor, parent clang.Cursor) {
	this.genArgs(cursor, parent)
	argStr := strings.Join(this.argDesc, ", ")
	this.genParams(cursor, parent)
	paramStr := strings.Join(this.paramDesc, ", ")

	pparent := parent.SemanticParent()
	pparentstr := ""
	if strings.HasPrefix(pparent.Spelling(), "Qt") {
		pparentstr = fmt.Sprintf("%s::", pparent.Spelling())
	}

	retstr := "void"
	retset := false
	rety := cursor.ResultType()
	cancpobj := has_copy_ctor(rety.Declaration()) || is_trivial_class(rety.Declaration())
	if isPrimitiveType(rety) {
		retstr = rety.Spelling()
		retset = true
	} else if rety.Kind() == clang.Type_Pointer {
		retstr = "void*"
		retset = true
	} else {
		if cancpobj {
			retstr = "void*"
		} else if rety.Kind() == clang.Type_LValueReference && TypeIsConsted(rety) {
			retstr = "void*"
		} else if rety.Kind() == clang.Type_LValueReference && !TypeIsConsted(rety) {
			retstr = "void*"
		}
	}

	this.cp.APf("main", "%s %s(%s) {", retstr, this.mangler.convTo(cursor), argStr)
	if cursor.ResultType().Kind() == clang.Type_Void {
		this.cp.APf("main", "  %s%s::%s(%s);", pparentstr, parent.Spelling(), cursor.Spelling(), paramStr)
	} else {
		if retset {
			this.cp.APf("main", "  return (%s)%s%s::%s(%s);", retstr, pparentstr, parent.Spelling(), cursor.Spelling(), paramStr)
		} else {
			// this.cp.APf("main", "  /*return*/ %s%s::%s(%s);", pparentstr, parent.Spelling(), cursor.Spelling(), paramStr)
			autoand := gopp.IfElseStr(rety.Kind() == clang.Type_LValueReference, "auto&", "auto")
			this.cp.APf("main", "  %s rv = %s%s::%s(%s);",
				autoand, pparentstr, parent.Spelling(), cursor.Spelling(), paramStr)

			if cancpobj {
				unconstystr := strings.Replace(rety.Spelling(), "const ", "", 1)
				this.cp.APf("main", "return new %s(rv);", unconstystr)
			} else if rety.Kind() == clang.Type_LValueReference && TypeIsConsted(rety) {
				unconstystr := strings.Replace(rety.PointeeType().Spelling(), "const ", "", 1)
				this.cp.APf("main", "return new %s(rv);", unconstystr)
			} else if rety.Kind() == clang.Type_LValueReference && !TypeIsConsted(rety) {
				this.cp.APf("main", "return &rv;")
			} else {
				this.cp.APf("main", "/*return rv;*/")
			}
		}
	}
	this.cp.APf("main", "}")
}

func (this *GenerateInline) genProtectedCallback(cursor, parent clang.Cursor) {
	this.genMethodHeader(cursor, parent)
	this.cp.APf("main", "void* callback%s = 0;", cursor.Mangling())
	this.cp.APf("main", "extern \"C\" void set_callback%s(void*cbfn)", cursor.Mangling())
	this.cp.APf("main", "{ callback%s = cbfn; }", cursor.Mangling())
}

func (this *GenerateInline) genArgs(cursor, parent clang.Cursor) {
	this.argDesc = make([]string, 0)
	for idx := 0; idx < int(cursor.NumArguments()); idx++ {
		argc := cursor.Argument(uint32(idx))
		this.genArg(argc, cursor, idx)
	}
	// log.Println(strings.Join(this.argDesc, ", "), this.mangler.convTo(cursor))
}

func (this *GenerateInline) genArg(cursor, parent clang.Cursor, idx int) {
	// log.Println(cursor.DisplayName(), cursor.Type().Spelling(), cursor.Type().Kind() == clang.Type_LValueReference, this.mangler.convTo(parent))

	if len(cursor.Spelling()) == 0 {
		this.argDesc = append(this.argDesc, fmt.Sprintf("%s arg%d", cursor.Type().Spelling(), idx))
	} else {
		if cursor.Type().Kind() == clang.Type_LValueReference {
			// 转成指针
		}
		if strings.Contains(cursor.Type().CanonicalType().Spelling(), "QFlags<") {
			this.argDesc = append(this.argDesc, fmt.Sprintf("%s %s",
				cursor.Type().CanonicalType().Spelling(), cursor.Spelling()))
		} else {
			log.Println(cursor.Type().Kind(), cursor.Type().Spelling(), parent.Spelling())
			if TypeIsFuncPointer(cursor.Type()) {
				this.argDesc = append(this.argDesc,
					strings.Replace(cursor.Type().Spelling(), "(*)",
						fmt.Sprintf("(*%s)", cursor.Spelling()), 1))
			} else if cursor.Type().Kind() == clang.Type_IncompleteArray ||
				cursor.Type().Kind() == clang.Type_ConstantArray {
				this.argDesc = append(this.argDesc, fmt.Sprintf("void *%s", cursor.Spelling()))
				// idx := strings.Index(cursor.Type().Spelling(), " [")
				// this.argDesc = append(this.argDesc, fmt.Sprintf("%s %s %s",
				//	cursor.Type().Spelling()[0:idx], cursor.Spelling(), cursor.Type().Spelling()[idx+1:]))
			} else {
				this.argDesc = append(this.argDesc, fmt.Sprintf("%s %s",
					cursor.Type().Spelling(), cursor.Spelling()))
			}
		}
	}
}

func (this *GenerateInline) genParams(cursor, parent clang.Cursor) {
	this.paramDesc = make([]string, 0)
	for idx := 0; idx < int(cursor.NumArguments()); idx++ {
		argc := cursor.Argument(uint32(idx))
		this.genParam(argc, cursor, idx)
	}
}

func (this *GenerateInline) genParam(cursor, parent clang.Cursor, idx int) {
	csty := cursor.Type()
	forceConvStr := ""
	log.Println(csty.Kind().String(), csty.Spelling(), parent.Spelling(), csty.PointeeType().Kind().String(), csty.ArrayElementType().Kind().String())
	if TypeIsCharPtrPtr(csty) {
		forceConvStr = "(char**)"
	}
	if len(cursor.Spelling()) == 0 {
		this.paramDesc = append(this.paramDesc, fmt.Sprintf("%sarg%d", forceConvStr, idx))
	} else {
		this.paramDesc = append(this.paramDesc, fmt.Sprintf("%s%s", forceConvStr, cursor.Spelling()))
	}
}

func (this *GenerateInline) genRet(cursor, parent clang.Cursor, idx int) {

}

//
func (this *GenerateInline) genCSignature(cursor, parent clang.Cursor, idx int) {

}

func (this *GenerateInline) genEnums() {

}
func (this *GenerateInline) genEnum() {

}
