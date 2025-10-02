module LangGeneric_python
open Asn1AcnAst
open CommonTypes
open System.Numerics
open DAst
open FsUtils
open Language
open System.IO
open System
open Asn1AcnAstUtilFunctions
// open ProofGen // TODO
// open ProofAst // TODO

let rec resolveReferenceType(t: Asn1TypeKind): Asn1TypeKind =
    match t with
    | ReferenceType rt -> resolveReferenceType rt.resolvedType.Kind
    | _ -> t

let isPythonPrimitive (t: Asn1TypeKind) =
    match resolveReferenceType t with
    | Integer _ | Real _ | NullType _ | Boolean _ -> true
    | _ -> false

let initMethSuffix k =
    match isPythonPrimitive k with
    | false ->
        match k with
        | BitString bitString -> ""
        | _ -> "()"
    | true -> ""

let isEnumForPythonelseFalse (k: Asn1TypeKind): bool =
    match ST.lang with
    | Python ->
        match resolveReferenceType k with
        | Enumerated e -> true
        | _ -> false
    | _ -> false

let isSequenceForPythonelseFalse (k: Asn1TypeKind): bool =
    match ST.lang with
    | Python ->
        match k with
        | Sequence s -> true
        | _ -> false
    | _ -> false

let isOctetStringForPythonelseFalse (k: Asn1TypeKind): bool =
    match ST.lang with
    | Python ->
        match k with
        | OctetString s -> true
        | _ -> false
    | _ -> false

let uperExprMethodCall (k: Asn1TypeKind) (sChildInitExpr: string) =
    let isSequence = isSequenceForPythonelseFalse k
    let isEnum = isEnumForPythonelseFalse k
    let isOctetString = isOctetStringForPythonelseFalse k

    match isSequence || sChildInitExpr.Equals("None") || isEnum || isOctetString with
    | true -> ""
    | false -> initMethSuffix k

type LangBasic_python() =
    inherit ILangBasic()
    
    override this.cmp (s1:string) (s2:string) = s1 = s2
    override this.isCaseSensitive = true
    override this.keywords = python_keywords
    override this.isKeyword (token) = python_keywords.Contains token
    override this.OnTypeNameConflictTryAppendModName = true
    override this.declare_IntegerNoRTL = "", "int", "INTEGER"
    override this.declare_PosIntegerNoRTL = "", "int", "INTEGER"
    override this.getRealRtlTypeName = "", "float", "REAL"
    override this.getObjectIdentifierRtlTypeName relativeId =
        let asn1Name = if relativeId then "RELATIVE-OID" else "OBJECT IDENTIFIER"
        "", "Asn1ObjectIdentifier", asn1Name
    override this.getTimeRtlTypeName timeClass =
        let asn1Name = "TIME"
        match timeClass with
        | Asn1LocalTime                    _ -> "", "Asn1LocalTime", asn1Name
        | Asn1UtcTime                      _ -> "", "Asn1UtcTime", asn1Name
        | Asn1LocalTimeWithTimeZone        _ -> "", "Asn1TimeWithTimeZone", asn1Name
        | Asn1Date                           -> "", "Asn1Date", asn1Name
        | Asn1Date_LocalTime               _ -> "", "Asn1DateLocalTime", asn1Name
        | Asn1Date_UtcTime                 _ -> "", "Asn1DateUtcTime", asn1Name
        | Asn1Date_LocalTimeWithTimeZone   _ -> "", "Asn1DateTimeWithTimeZone", asn1Name
    override this.getNullRtlTypeName = "", "None", "NULL"
    override this.getBoolRtlTypeName = "", "bool", "BOOLEAN"

let isClassVariable (receiverId: string) : bool =
        // For Python class methods, we need to detect when the receiverId should be treated as "self"
        // Class methods are generated via EmitTypeAssignment_composite template which expects self parameter
        // We detect this by checking if we're in a context where the receiverId should reference the class instance
        receiverId = "self" || receiverId.StartsWith("self")
        
type LangGeneric_python() =
    inherit ILangGeneric()
    
    override _.ArrayStartIndex = 0
    
    override _.intValueToString (i:BigInteger) (intClass:Asn1AcnAst.IntegerClass) =
        match intClass with
        | Asn1AcnAst.ASN1SCC_Int8     _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_Int16    _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_Int32    _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_Int64    _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_Int _ when
            i >= BigInteger System.Int32.MinValue &&
            i <= BigInteger System.Int32.MaxValue ->
                sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_Int      _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_UInt8    _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_UInt16   _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_UInt32   _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_UInt64   _ ->  sprintf "%s" (i.ToString())
        | Asn1AcnAst.ASN1SCC_UInt     _ ->  sprintf "%s" (i.ToString())

    override _.asn1SccIntValueToString (i: BigInteger) (unsigned: bool) =
        let iStr = i.ToString()
        if unsigned then iStr else iStr

    override _.doubleValueToString (v:double) =
        v.ToString(FsUtils.doubleParseString, System.Globalization.NumberFormatInfo.InvariantInfo)

    override _.initializeString stringSize = sprintf "\"0\" * %d" stringSize

    override _.supportsInitExpressions = true

    override this.getPointer (sel: Selection) = sel.joined this

    override this.getValue (sel: Selection) = sel.joined this        
    override this.getValueUnchecked (sel: Selection) (kind: UncheckedAccessKind) = this.joinSelectionUnchecked sel kind
    override this.getPointerUnchecked (sel: Selection) (kind: UncheckedAccessKind) = this.joinSelectionUnchecked sel kind
    override _.joinSelectionUnchecked (sel: Selection) (kind: UncheckedAccessKind) =
        let len = sel.path.Length
        let receiverPrefix = if isClassVariable sel.receiverId then "self." else ""
        List.fold (fun str (ix, accessor) ->
            let accStr =
                match accessor with
                | ValueAccess (id, _, isOpt) ->
                    if isOpt && (kind = FullAccess || ix < len - 1) then $".{id}" else $".{id}"
                | PointerAccess (id, _, isOpt) ->
                    if isOpt && (kind = FullAccess || ix < len - 1) then $".{id}" else $".{id}"
                | ArrayAccess (ix, _) -> $"[{ix}]"
            $"{str}{accStr}"
        ) (receiverPrefix + sel.receiverId) (List.indexed sel.path)
    
    override this.getAccess (sel: Selection) = "."

    override this.getAccess2 (acc: Accessor) =
        match acc with
            | ValueAccess (sel, _, _) -> $".{sel}"
            | PointerAccess (sel, _, _) -> $".{sel}"
            | ArrayAccess (ix, _) -> $"[{ix}]"

    override this.getPtrPrefix _ = ""

    override this.getPtrSuffix _ = ""

    override this.getStar _ = ""

    override _.real_annotations = []

    override this.getArrayItem (sel: Selection) (idx:string) (childTypeIsString: bool) = 
        (sel.appendSelection "arr" FixArray false).append (ArrayAccess (idx, if childTypeIsString then FixArray else Value))

    override this.getNamedItemBackendName (defOrRef: TypeDefinitionOrReference option) (nm: Asn1AcnAst.NamedItem) =
        let itemname =
            match defOrRef with
            | Some (TypeDefinition td) -> td.typedefName + "." + ToC nm.python_name
            | Some (ReferenceToExistingDefinition rted) -> rted.typedefName + "." + ToC nm.python_name
            | _ -> ToC nm.python_name
        itemname

    override this.getNamedItemBackendName0 (nm:Asn1Ast.NamedItem) = nm.python_name
    override this.setNamedItemBackendName0 (nm:Asn1Ast.NamedItem) (newValue:string) : Asn1Ast.NamedItem =
        {nm with python_name = newValue}

    override this.getNamedItemBackendName2 (_:string) (_:string) (nm:Asn1AcnAst.NamedItem) =
        ToC nm.python_name

    override this.decodeEmptySeq _ = None
    override this.decode_nullType _ = None

    override this.Length exp sAcc =
        isvalid_python.ArrayLen exp sAcc

    override this.typeDef (ptd:Map<ProgrammingLanguage, FE_PrimitiveTypeDefinition>) = ptd.[Python]
    override this.definitionOrRef (d:Map<ProgrammingLanguage, TypeDefinitionOrReference>) = d.[Python]
    override this.getTypeDefinition (td:Map<ProgrammingLanguage, FE_TypeDefinition>) = td.[Python]
    override this.getEnumTypeDefinition (td:Map<ProgrammingLanguage, FE_EnumeratedTypeDefinition>) = td.[Python]
    override this.getStrTypeDefinition (td:Map<ProgrammingLanguage, FE_StringTypeDefinition>) = td.[Python]
    override this.getChoiceTypeDefinition (td:Map<ProgrammingLanguage, FE_ChoiceTypeDefinition>) = td.[Python]
    override this.getSequenceTypeDefinition (td:Map<ProgrammingLanguage, FE_SequenceTypeDefinition>) = td.[Python]
    override this.getSizeableTypeDefinition (td:Map<ProgrammingLanguage, FE_SizeableTypeDefinition>) = td.[Python]
    override this.getAsn1ChildBackendName (ch:Asn1Child) = ch._python_name
    override this.getAsn1ChChildBackendName (ch:ChChildInfo) = ch._python_name
    override _.getChildInfoName (ch:Asn1Ast.ChildInfo) = ch.python_name
    override _.setChildInfoName (ch:Asn1Ast.ChildInfo) (newValue:string) = {ch with python_name = newValue}
    override this.getAsn1ChildBackendName0 (ch:Asn1AcnAst.Asn1Child) = ch._python_name
    override this.getAsn1ChChildBackendName0 (ch:Asn1AcnAst.ChChildInfo) = ch._python_name
    override _.getChoiceChildPresentWhenName (ch:Asn1AcnAst.Choice) (c:Asn1AcnAst.ChChildInfo) : string =
        ch.typeDef[Python].typeName + "." + (ToC c.present_when_name)

    override this.constructReferenceFuncName (baseTypeDefinitionName: string) (codecName: string) (methodSuffix: string): string =
        methodSuffix

    override this.constructFuncName (baseTypeDefinitionName: string) (codecName: string) (methodSuffix: string): string =
        baseTypeDefinitionName + "." + methodSuffix

    override this.getFuncNameGeneric (typeDefinition:TypeDefinitionOrReference) (nameSuffix: string): string option  =
        match typeDefinition with
        | ReferenceToExistingDefinition  refEx  -> None
        | TypeDefinition   td                   -> Some nameSuffix

    override this.getUPerFuncName (r:Asn1AcnAst.AstRoot) (codec:CommonTypes.Codec) (t: Asn1AcnAst.Asn1Type) (td:FE_TypeDefinition): option<string> =
        this.getACNFuncName r codec t td

    override this.getACNFuncName (r:Asn1AcnAst.AstRoot) (codec:CommonTypes.Codec) (t: Asn1AcnAst.Asn1Type) (td:FE_TypeDefinition): string option = 
        match t.acnParameters with
        | []    ->
            match t.id.tasInfo with
            | None -> None
            | Some _ -> Some codec.suffix
        | _     -> None

    override this.getRtlFiles (encodings:Asn1Encoding list) (_ :string list) =
        let encRtl = match encodings |> Seq.exists(fun e -> e = UPER || e = ACN ) with true -> ["asn1crt_encoding"] | false -> []
        let uperRtl = match encodings |> Seq.exists(fun e -> e = UPER || e = ACN) with true -> ["asn1crt_encoding_uper"] | false -> []
        let acnRtl = match encodings |> Seq.exists(fun e -> e = ACN) with true -> ["asn1crt_encoding_acn"] | false -> []
        let xerRtl = match encodings |> Seq.exists(fun e -> e = XER) with true -> ["asn1crt_encoding_xer"] | false -> []
        encRtl@uperRtl@acnRtl@xerRtl

    override this.getEmptySequenceInitExpression sTypeDefName = $"{sTypeDefName}()"
    override this.callFuncWithNoArgs () = "()"
    override this.rtlModuleName = ""
    override this.AssignOperator = "="
    override this.TrueLiteral = "True"
    override this.FalseLiteral = "False"
    override this.emptyStatement = ""
    override this.bitStreamName = "BitStream"
    override this.unaryNotOperator = "not"
    override this.modOp = "%"
    override this.eqOp = "=="
    override this.neqOp = "!="
    override this.andOp = "and"
    override this.orOp = "or"
    override this.initMethod = InitMethod.Procedure
    override _.decodingKind = Copy
    override _.usesWrappedOptional = false
    override this.castExpression (sExp:string) (sCastType:string) = sprintf "%s(%s)" sCastType sExp
    override this.createSingleLineComment (sText:string) = sprintf "#%s" sText

    // In case of Python, there is no Spec and Body file distinction. We use no Suffix and use Append in GenerateFiles.fs to merge the spec & body into the same file.
    override _.SpecNameSuffix = ""
    override _.SpecExtension = "py"
    override _.BodyExtension = "py"
    override _.isFilenameCaseSensitive = true
    
    override _.Keywords = CommonTypes.python_keywords

    override _.getValueAssignmentName (vas: ValueAssignment) = vas.python_name

    override this.hasModules = true
    override this.allowsSrcFilesWithNoFunctions = true
    override this.requiresValueAssignmentsInSrcFile = false
    override this.supportsStaticVerification = false

    override this.getSeqChildIsPresent (sel: Selection) (childName: string) =
        sprintf "%s%s%s is not None" (sel.joined this) (this.getAccess sel) childName

    override this.getSeqChild (sel: Selection) (childName:string) (childTypeIsString: bool) (childIsOptional: bool) =
        sel.appendSelection childName (if childTypeIsString then FixArray else Value) childIsOptional

    override this.getChChild (sel: Selection) (childName:string) (childTypeIsString: bool) : Selection =
        sel.appendSelection "data" Value false

    override this.choiceIDForNone (typeIdsSet:Map<string,int>) (id:ReferenceToType) = ""

    override this.presentWhenName (defOrRef:TypeDefinitionOrReference option) (ch:ChChildInfo) : string =
        let parentName =
            match defOrRef with
            | Some a -> match a with
                        | ReferenceToExistingDefinition b -> b.typedefName + "."
                        | TypeDefinition c -> c.typedefName + "."
            | None -> ""
        parentName + (ToC ch._present_when_name_private)

    override this.presentWhenName0 (defOrRef:TypeDefinitionOrReference option) (ch:Asn1AcnAst.ChChildInfo) : string =
        let parentName =
            match defOrRef with
            | Some a -> match a with
                        | ReferenceToExistingDefinition b -> b.typedefName + "."
                        | TypeDefinition c -> c.typedefName + "."
            | None -> ""
        parentName + (ToC ch.present_when_name)

    override this.getParamTypeSuffix (t:Asn1AcnAst.Asn1Type) (suf:string) (c:Codec) : CallerScope =
        let p = this.getParamType t c
        {p with arg.receiverId = p.arg.receiverId + suf}
    
    override this.getParamType (t:Asn1AcnAst.Asn1Type) (c:Codec) : CallerScope =
        let rec getRecvType (kind: Asn1AcnAst.Asn1TypeKind) =
            match kind with
            | Asn1AcnAst.NumericString _ | Asn1AcnAst.IA5String _ -> FixArray
            | Asn1AcnAst.ReferenceType r -> getRecvType r.resolvedType.Kind
            | _ -> Pointer
        let recvId = match c with
                        | Decode -> "instance"
                        | Encode ->
                            match t.Kind with
                            | Asn1AcnAst.Enumerated _ -> "self.val" // For enums, we encapsulate the inner value into a "val" object
                            | _ -> "self"                           // For class methods, the receiver is always "self"
        
        {CallerScope.modName = t.id.ModName; arg = Selection.emptyPath recvId (getRecvType t.Kind) }

    override this.getParamValue (t:Asn1AcnAst.Asn1Type) (p:Selection) (c:Codec) =
        p.joined this

    override this.getLocalVariableDeclaration (lv:LocalVariable) : string =
        match lv with
        | SequenceOfIndex (i,None)                  -> sprintf "i%d = 0" i
        | SequenceOfIndex (i,Some iv)               -> sprintf "i%d = %s" i iv
        | IntegerLocalVariable (name,None)          -> sprintf "%s = 0" name
        | IntegerLocalVariable (name,Some iv)       -> sprintf "%s = %s" name iv
        | Asn1SIntLocalVariable (name,None)         -> sprintf "%s = 0" name
        | Asn1SIntLocalVariable (name,Some iv)      -> sprintf "%s = %s" name iv
        | Asn1UIntLocalVariable (name,None)         -> sprintf "%s = 0" name
        | Asn1UIntLocalVariable (name,Some iv)      -> sprintf "%s = %s" name iv
        | FlagLocalVariable (name,None)             -> sprintf "%s = False" name
        | FlagLocalVariable (name,Some iv)          -> sprintf "%s = %s" name iv
        | BooleanLocalVariable (name,None)          -> sprintf "%s = False" name
        | BooleanLocalVariable (name,Some iv)       -> sprintf "%s = %s" name iv
        | AcnInsertedChild(name, vartype, initVal)  ->
            sprintf "%s = %s" name initVal
        | GenericLocalVariable lv                   ->
            sprintf "%s = %s" lv.name (if lv.initExp.IsNone then "None" else lv.initExp.Value)

    override this.getLongTypedefName (tdr:TypeDefinitionOrReference) : string =
        match tdr with
        | TypeDefinition  td -> td.typedefName
        | ReferenceToExistingDefinition ref -> ref.typedefName

    override this.toHex n = sprintf "0x%x" n

    override this.bitStringValueToByteArray (v : BitStringValue) = 
        FsUtils.bitStringValueToByteArray (StringLoc.ByValue v)

    override this.getTopLevelDirs (target:Targets option) = []

    override this.getDirInfo (target:Targets option) rootDir =
         let rootDir = Path.Combine(rootDir, "asn1pylib")
         let di = {
          rootDir = rootDir
          srcDir = Path.Combine(rootDir, "asn1src")
          asn1rtlDir = Path.Combine(rootDir, "asn1python")
          boardsDir = rootDir
         }
         Directory.CreateDirectory di.rootDir |> ignore         
         Directory.CreateDirectory di.srcDir |> ignore         
         Directory.CreateDirectory di.asn1rtlDir |> ignore         
         di

    override this.getChChildIsPresent (arg:Selection) (chParent:string) (pre_name:string) =
        sprintf "isinstance(%s, %s.%s_PRESENT)" (arg.joined this) chParent pre_name

    override this.CreateMakeFile (r:AstRoot) (di:DirInfo) =
        let printPyproject = aux_python.PrintMakeFile
        let content = printPyproject [""] false false false
        File.WriteAllText(Path.Combine(di.rootDir, "pyproject.toml"), content)

    override this.CreateAuxFiles (r:AstRoot) (di:DirInfo) (arrsSrcTstFiles : string list, arrsHdrTstFiles:string list) =
        let CreatePythonMainFile (r:AstRoot) outDir  =
            // Main file for test case
            let printMain = test_cases_python.PrintMain
            let content = printMain "testsuite"
            let outFileName = Path.Combine(outDir, "mainprogram.py")
            File.WriteAllText(outFileName, content.Replace("\r",""))

        CreatePythonMainFile r di.srcDir

    override this.uper =
        {
            Uper_parts.createLv = (fun name -> Asn1SIntLocalVariable(name,None))
            requires_sBlockIndex  = true
            requires_sBLJ = false
            requires_charIndex = false
            requires_IA5String_i = true
            count_var            = Asn1SIntLocalVariable ("nCount", None)
            requires_presenceBit = false
            catd                 = false
            seqof_lv              =
              (fun id minSize maxSize -> [SequenceOfIndex (id.SequenceOfLevel + 1, None)])
            exprMethodCall = uperExprMethodCall
        }

    override this.acn =
        {
            Acn_parts.null_valIsUnReferenced = true
            checkBitPatternPresentResult = true
            getAcnContainingByLocVars = fun _ -> []
            getAcnDepSizeDeterminantLocVars =
                fun  sReqBytesForUperEncoding ->
                    [
                        GenericLocalVariable {GenericLocalVariable.name = "arr"; varType = "bytearray"; arrSize = Some sReqBytesForUperEncoding; isStatic = false; initExp = None}
                        GenericLocalVariable {GenericLocalVariable.name = "bitStrm"; varType = "BitStream"; arrSize = None; isStatic = false; initExp = None}
                    ]
            createLocalVariableEnum =
                (fun rtlIntType -> GenericLocalVariable {GenericLocalVariable.name = "intVal"; varType= rtlIntType; arrSize= None; isStatic = false; initExp= (Some("0")) })
            choice_handle_always_absent_child = false
            choice_requires_tmp_decoding = false
        }

    override this.init =
        {
            Initialize_parts.zeroIA5String_localVars    = fun _ -> []
            choiceComponentTempInit                     = false
            initMethSuffix                              = initMethSuffix
        }

    override this.atc =
        {
            Atc_parts.uperPrefix = ""
            acnPrefix            = "ACN_"
            xerPrefix            = "XER_"
            berPrefix            = "BER_"
        }

    override this.extractEnumClassName (prefix: String)(varName: String)(internalName: String): String =
        prefix + varName.Substring(0, max 0 (varName.Length - (internalName.Length + 1)))
        
    override _.getTypeBasedSuffix (fType: FunctionType) (kind: Asn1AcnAst.Asn1TypeKind) =
        match (kind, fType) with
        | Asn1AcnAst.Asn1TypeKind.Choice _, IsValidFunctionType -> ""
        | _ -> ""

    // Placeholder methods for features not yet implemented in Python
    // override this.generateSequenceAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (sq: Asn1AcnAst.Sequence) (nestingScope: NestingScope) (sel: Selection) (codec: Codec): string list =
    //     []

    // override this.generateIntegerAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (int: Asn1AcnAst.Integer) (nestingScope: NestingScope) (sel: Selection) (codec: Codec): string list =
    //     []

    // override this.generateBooleanAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (boolean: Asn1AcnAst.Boolean) (nestingScope: NestingScope) (sel: Selection) (codec: Codec): string list =
    //     []

    // override this.generateSequenceOfLikeAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (o: SequenceOfLike) (pg: SequenceOfLikeProofGen) (codec: Codec): string list * string option =
    //     [], None

    // override this.generateOptionalAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (soc: SequenceOptionalChild) (codec: Codec): string list * string =
    //     [], ""

    // override this.generateChoiceAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (ch: Asn1AcnAst.Choice) (nestingScope: NestingScope) (sel: Selection) (codec: Codec): string list =
    //     []

    // override this.generateNullTypeAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (nt: Asn1AcnAst.NullType) (nestingScope: NestingScope) (sel: Selection) (codec: Codec): string list =
    //     []

    // override this.generateEnumAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (enm: Asn1AcnAst.Enumerated) (nestingScope: NestingScope) (sel: Selection) (codec: Codec): string list =
    //     []

    // override this.adaptAcnFuncBody (r: Asn1AcnAst.AstRoot) (deps: Asn1AcnAst.AcnInsertedFieldDependencies) (funcBody: AcnFuncBody) (isValidFuncName: string option) (t: Asn1AcnAst.Asn1Type) (codec: Codec): AcnFuncBody =
    //     funcBody

    // override this.generatePrecond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (codec: Codec): string list =
    //     []

    // override this.generatePostcond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (p: CallerScope) (t: Asn1AcnAst.Asn1Type) (codec: Codec) =
    //     None

    // override this.generateSequenceChildProof (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (stmts: string option list) (pg: SequenceProofGen) (codec: Codec): string list =
    //     []

    // override this.generateSequenceProof (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (sq: Asn1AcnAst.Sequence) (nestingScope: NestingScope) (sel: Selection) (codec: Codec): string list =
    //     []

    // override this.generateSequenceOfLikeProof (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (o: SequenceOfLike) (pg: SequenceOfLikeProofGen) (codec: Codec): SequenceOfLikeProofGenResult option =
    //     None

    // override this.generateIntFullyConstraintRangeAssert (topLevelTd: string) (p: CallerScope) (codec: Codec): string option =
    //     None

    // override this.generateOctetStringInvariants (minSize : SIZE) (maxSize : SIZE): string list =
    //     []

    // override this.generateBitStringInvariants (minSize : SIZE) (maxSize : SIZE): string list =
    //     []

    // override this.generateSequenceInvariants (children: Asn1AcnAst.Asn1Child list): string list =
    //     []

    // override this.generateSequenceOfInvariants (minSize : SIZE) (maxSize : SIZE) : string list =
    //     []

    // override this.generateSequenceSizeDefinitions (acnAlignment : AcnGenericTypes.AcnAlignment option) (maxAlignment: AcnGenericTypes.AcnAlignment option) (acnMinSizeInBits : BigInteger) (acnMaxSizeInBits : BigInteger) (children : Asn1AcnAst.SeqChildInfo list): string list =
    //     []

    // override this.generateChoiceSizeDefinitions (acnAlignment : AcnGenericTypes.AcnAlignment option) (maxAlignment: AcnGenericTypes.AcnAlignment option)
    //               (acnMinSizeInBits    : BigInteger)
    //               (acnMaxSizeInBits    : BigInteger)
    //               (typeDef : Map<ProgrammingLanguage, FE_ChoiceTypeDefinition>) 
    //               (children            : Asn1AcnAst.ChChildInfo list): string list =
    //     []

    // override this.generateSequenceOfSizeDefinitions (typeDef : Map<ProgrammingLanguage, FE_SizeableTypeDefinition>) (acnMinSizeInBits : BigInteger) (acnMaxSizeInBits : BigInteger) (maxSize : SIZE) (acnEncodingClass : Asn1AcnAst.SizeableAcnEncodingClass) (acnAlignment : AcnGenericTypes.AcnAlignment option) (maxAlignment: AcnGenericTypes.AcnAlignment option) (child : Asn1AcnAst.Asn1Type): string list * string list =
    //     [], []

    // override this.generateSequenceSubtypeDefinitions (dealiased: string) (typeDef:Map<ProgrammingLanguage, FE_SequenceTypeDefinition>) (children: Asn1AcnAst.Asn1Child list): string list =
    //     []