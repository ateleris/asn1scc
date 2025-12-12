module GenerateFiles

open System
open System.IO

open FsUtils
open CommonTypes
open DAst
open DAstUtilFunctions
open Language
open Microsoft.FSharp.Collections


let getTypeDecl = DastTestCaseCreation.getTypeDecl

let rec getValidFunctions (isValidFunction:IsValidFunction) =
    seq {
        for c in isValidFunction.nonEmbeddedChildrenValidFuncs do
            yield! getValidFunctions c
        yield isValidFunction
    } |> Seq.toList

let rec getInitializationFunctions (isValidFunction:InitFunction) =
    seq {
        for c in isValidFunction.nonEmbeddedChildrenFuncs do
            yield! getInitializationFunctions c
        yield isValidFunction
    } |> Seq.toList

let printHeaderFileValueAssignment (r:DAst.AstRoot) (vasPU_name:string)  (lm:LanguageMacros) (vas:ValueAssignment) =
    let sName = vas.c_name
    let t = vas.Type
    let sTypeDecl= getTypeDecl r vasPU_name lm vas

    let sVal = DAstVariables.printValue r  lm vasPU_name vas.Type None vas.Value.kind
    lm.typeDef.PrintValueAssignment sName sTypeDecl sVal

let printSourceFileValueAssignment (r:DAst.AstRoot) (vasPU_name:string)  (lm:LanguageMacros) (vas:ValueAssignment) =
    let sName = vas.c_name
    let t = vas.Type
    let sTypeDecl: string= getTypeDecl r vasPU_name lm vas
    let sVal = DAstVariables.printValue r  lm vasPU_name vas.Type None vas.Value.kind
    lm.vars.PrintValueAssignment sName sTypeDecl sVal

let rec collectEqualFuncs (t:Asn1Type) =
    seq {
        match t.Kind with
        | Integer          _
        | Real             _
        | IA5String        _
        | OctetString      _
        | NullType         _
        | BitString        _
        | Boolean          _
        | ObjectIdentifier _
        | TimeType         _
        | Enumerated       _ -> ()
        | SequenceOf        ch ->
            yield! collectEqualFuncs ch.childType
        | Sequence        sq ->
            for ch in sq.children do
                match ch with
                | Asn1Child ch  -> yield! collectEqualFuncs ch.Type
                | AcnChild  _   -> ()
        | Choice          ch ->
            for c in ch.children do
                yield! collectEqualFuncs c.chType
        | ReferenceType     _   -> ()
        yield t.equalFunction
    } |> Seq.toList


let private combineStringOpts(a: string option) (b: string option) = (defaultArg a "") + "\n" + (defaultArg b "")

let private printUnit (r:DAst.AstRoot)  (lm:LanguageMacros) (encodings: CommonTypes.Asn1Encoding list) outDir (pu:ProgramUnit)  =
    let tases = pu.sortedTypeAssignments
    let printChildrenIsValidFuncs (t:Asn1Type) =
        match t.Kind with
        | SequenceOf o  -> o.Cons.IsEmpty
        | Sequence o    -> o.Cons.IsEmpty
        | Choice o      -> o.Cons.IsEmpty
        | _             -> false


    let vases = pu.valueAssignments
    let arrsAnonymousValues =
        pu.sortedTypeAssignments |>
        List.choose(fun z -> z.Type.isValidFunction) |>
        List.collect (fun z -> z.anonymousVariables)  |>
        Seq.distinctBy(fun z -> z.valueName) |>
        Seq.toList

    let requiresUPER = encodings |> Seq.exists ( (=) Asn1Encoding.UPER)
    let requiresAcn = encodings |> Seq.exists ( (=) Asn1Encoding.ACN)
      
    let (definitionsContntent, srcBody) =
        match r.lang with
        | Python ->
            // Helper function to detect if a type uses deep field access (inline ACN encoding)
            let rec typeHasDeepFieldAccess (t: Asn1Type) : bool =
                match t.Kind with
                | Sequence seq ->
                    // Check if this sequence has ACN children (inline ACN encoding)
                    let hasAcnChildren = seq.children |> List.exists (function | AcnChild _ -> true | _ -> false)
                    if hasAcnChildren then
                        true
                    else
                        // Recursively check children
                        seq.Asn1Children |> List.exists (fun ch -> typeHasDeepFieldAccess ch.Type)
                | SequenceOf o ->
                    typeHasDeepFieldAccess o.childType
                | Choice ch ->
                    ch.children |> List.exists (fun c -> typeHasDeepFieldAccess c.chType)
                | ReferenceType rt ->
                    // Check the resolved type
                    typeHasDeepFieldAccess rt.resolvedType
                | _ ->
                    false

            // STEP 1: Pre-process types with deep field access
            // Build a map: typeId -> generated code string
            let deepFieldAccessMap =
                let tasesNeedingDeepFieldAccess =
                    tases |> List.filter (fun tas -> typeHasDeepFieldAccess tas.Type)

                if tasesNeedingDeepFieldAccess.IsEmpty then
                    Map.empty
                else
                    // Flatten and deduplicate types with deep field access
                    // Collect ALL types from these tases, pairing each with its source TAS
                    let allTypesFromAllTases =
                        tasesNeedingDeepFieldAccess |>
                        List.collect(fun tas ->
                            // Custom recursive function that follows references and gets RESOLVED types
                            let rec getMyselfAndChildrenResolved (t:Asn1Type) : Asn1Type list =
                                [
                                    // Yield the current type (might be a reference or actual type)
                                    yield t

                                    // Recursively process children based on kind
                                    match t.Kind with
                                    | SequenceOf o ->
                                        yield! getMyselfAndChildrenResolved o.childType
                                    | Sequence o   ->
                                        for ch in o.Asn1Children do
                                            yield! getMyselfAndChildrenResolved ch.Type
                                    | Choice o ->
                                        for ch in o.children do
                                            yield! getMyselfAndChildrenResolved ch.chType
                                    | ReferenceType rt ->
                                        // Follow the reference and get the resolved type
                                        // This resolved type will have the ACN context from where it's used
                                        yield! getMyselfAndChildrenResolved rt.resolvedType
                                    | _ -> ()
                                ]

                            let allChildrenRaw = getMyselfAndChildrenResolved tas.Type

                            // Keep types that should generate code:
                            // 1. Types with TypeDefinition (top-level TAS types)
                            // 2. Resolved Sequences/Choices (even if they don't have TypeDefinition)
                            // Skip: ReferenceTypes (already resolved), primitive fields
                            let allChildren =
                                allChildrenRaw
                                // Remove all children that are not defined in the current PU -> No deep field access over module boundaries according to ACN User Manual Chapter 4.2
                                |> List.filter (fun t -> ToC t.moduleName = ToC pu.name)
                                |> List.filter (fun t ->
                                    match t.typeDefinitionOrReference.IsTypeDefinition, t.Kind with
                                    | true, _ -> true  // Keep all types with TypeDefinition
                                    | false, Sequence _ -> true  // Keep resolved Sequences
                                    | false, SequenceOf _ -> true  // Keep resolved SequenceOfs
                                    | false, Choice _ -> true    // Keep resolved Choices
                                    | false, _ -> false  // Skip everything else (primitives, references)
                                )

                            // Pair each type with its source TAS so we can access tasInfo later
                            allChildren |> List.map (fun t -> (tas, t))
                        )

                    // Deduplicate by type name (not full path), keeping the version with more children
                    // (which will be the one with inline ACN encoding from parent context)
                    let deduplicatedTypes =
                        allTypesFromAllTases
                        |> List.groupBy (fun (tas, t) ->
                            // Group by the base type name using tasInfo
                            t.id.AsString
                            // match t.tasInfo with
                            // | Some ti -> $"{ti.modName}.{ti.tasName}"
                            // | None -> t.id.AsString  // Fallback to full path if no tasInfo
                        )
                        |> List.map (fun (typeKey, tasTypePairs) ->
                            // Pick the "richest" version - the one with more children in its Sequence
                            // This ensures we get types with inline ACN children from parent context
                            let chosen = tasTypePairs |> List.maxBy (fun (tas, t) ->
                                match t.Kind with
                                | Sequence seq -> seq.children.Length
                                | _ -> 0
                            )
                            chosen
                        )

                    // Generate code for each unique type (with correct ACN context)
                    deduplicatedTypes |> List.map(fun (tas, cls) ->
                        // Use the parent TAS's tasInfo for Caller construction
                        let typeAssignmentInfo = tas.Type.id.tasInfo.Value
                        let f cl = {Caller.typeId = typeAssignmentInfo; funcType = cl}
                        
                        // We backup the deep access definition type - we need that for acn enc/dec functions
                        let acnDeepAccessDefinitionType = cls
                        
                        // Then we overwrite cls with the tas or rootLevelTas type
                        let isFullDefinition, cls  =
                            match cls.typeDefinitionOrReference with
                            | TypeDefinition td ->
                                Console.WriteLine($"[1] Input: %s{cls.id.AsString}. Output: {tas.Type.id.AsString}")
                                true, tas.Type
                            | ReferenceToExistingDefinition ref ->
                                let myTas = tasesNeedingDeepFieldAccess |> List.filter(fun tas -> ToC tas.python_name = ToC ref.typedefName)
                                if myTas.Length = 0 then
                                    Console.WriteLine($"[2] Input: %s{cls.id.AsString}. Output: {tas.Type.id.AsString}")
                                    // Console.WriteLine($"Had some issues getting the original reference for %s{ref.typedefName}. Using other instead. Check manually!")
                                    false, tas.Type
                                else
                                    let myTas = myTas |> List.head
                                    Console.WriteLine($"[3] Input: %s{cls.id.AsString}. Output: {myTas.Type.id.AsString}")
                                    false, myTas.Type

                        let type_definition =
                            match cls.typeDefinitionOrReference with
                            | TypeDefinition td -> td.typedefBodyOnly ()
                            | ReferenceToExistingDefinition _ -> raise(BugErrorException "Type Assignment with no Type Definition")

                        let init_funcs        =
                            match r.callersSet |> Set.contains (f InitFunctionType) with
                            | true -> match cls.initFunction.initProcedure with | Some k -> k.body | None -> ""
                            | false -> ""

                        // todo: do we need special init funcs? how can they look like?
                        let special_init_funcs =
                            cls.initFunction.user_aux_functions |> List.map fst

                        let equal_funcs =
                            match r.args.GenerateEqualFunctions && (r.callersSet |> Set.contains (f EqualFunctionType)) with
                            | true  -> combineStringOpts cls.equalFunction.isEqualFuncDef cls.equalFunction.isEqualFunc
                            | false -> ""

                        let is_valid_funcs =
                            match r.callersSet |> Set.contains (f IsValidFunctionType) with
                            | false -> ""
                            | true  ->
                                match cls.isValidFunction with
                                | None      -> ""
                                | Some f    -> combineStringOpts f.funcDef f.func

                        let uPerEncFunc = match requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType) with true -> Some(combineStringOpts acnDeepAccessDefinitionType.uperEncFunction.funcDef acnDeepAccessDefinitionType.uperEncFunction.func) | false -> None
                        let uPerDecFunc = match requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType) with true -> Some(combineStringOpts acnDeepAccessDefinitionType.uperDecFunction.funcDef acnDeepAccessDefinitionType.uperDecFunction.func) | false -> None

                        let xerEncFunc = match acnDeepAccessDefinitionType.xerEncFunction with XerFunction z -> Some(combineStringOpts z.funcDef z.func) | XerFunctionDummy -> None
                        let xerDecFunc = match acnDeepAccessDefinitionType.xerDecFunction with XerFunction z -> Some(combineStringOpts z.funcDef z.func) | XerFunctionDummy -> None

                        let hasAcnEncDec = r.callersSet |> Set.contains (f AcnEncDecFunctionType)
                        let acnEncFunc, sEncodingSizeConstant =
                            match hasAcnEncDec && requiresAcn, acnDeepAccessDefinitionType.acnEncFunction with
                            | true, Some x -> Some (combineStringOpts x.funcDef x.func), Some x.encodingSizeConstant
                            | _  -> None, None
                        let acnDecFunc =
                            match hasAcnEncDec && requiresAcn, acnDeepAccessDefinitionType.acnDecFunction with
                            | true, Some x -> Some(combineStringOpts x.funcDef x.func)
                            | _ -> None

                        let allProcs = [equal_funcs]@[is_valid_funcs]@special_init_funcs@[init_funcs]@([uPerEncFunc;uPerDecFunc;sEncodingSizeConstant; acnEncFunc; acnDecFunc;xerEncFunc;xerDecFunc] |> List.choose id)
                        let generatedCode = lm.typeDef.Define_TAS type_definition allProcs
                        (cls.id.AsString, generatedCode)
                    )
                    |> Map.ofList

            // STEP 2: Process tases in original order, using map for deep field access types
            let typeDefs =
                tases |> List.collect(fun tas ->
                    let typeId = tas.Type.id.AsString

                    // Check if this type is in the deep field access map
                    if deepFieldAccessMap.ContainsKey(typeId) then
                        // Use pre-processed result with correct ACN context
                        [deepFieldAccessMap.[typeId]]
                    else
                        // Use simple approach for types without deep field access
                        // Get all nested children (just like the old code did)
                        let allChildren = GetMySelfAndChildren tas.Type
                                          |> List.filter _.typeDefinitionOrReference.IsTypeDefinition

                        let typeAssignmentInfo = tas.Type.id.tasInfo.Value
                        let f cl = {Caller.typeId = typeAssignmentInfo; funcType = cl}

                        // Generate code for each child type (including the top-level type itself)
                        allChildren |> List.map(fun cls ->
                            let type_definition =
                                match cls.typeDefinitionOrReference with
                                | TypeDefinition td -> td.typedefBodyOnly ()
                                | ReferenceToExistingDefinition _ -> raise(BugErrorException "Type Assignment with no Type Definition")

                            let init_funcs =
                                match r.callersSet |> Set.contains (f InitFunctionType) with
                                | true -> match cls.initFunction.initProcedure with | Some k -> k.body | None -> ""
                                | false -> ""

                            let special_init_funcs =
                                cls.initFunction.user_aux_functions |> List.map fst

                            let equal_funcs =
                                match r.args.GenerateEqualFunctions && (r.callersSet |> Set.contains (f EqualFunctionType)) with
                                | true -> combineStringOpts cls.equalFunction.isEqualFuncDef cls.equalFunction.isEqualFunc
                                | false -> ""

                            let is_valid_funcs =
                                match r.callersSet |> Set.contains (f IsValidFunctionType) with
                                | false -> ""
                                | true ->
                                    match cls.isValidFunction with
                                    | None -> ""
                                    | Some f -> combineStringOpts f.funcDef f.func

                            let uPerEncFunc = match requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType) with true -> Some(combineStringOpts cls.uperEncFunction.funcDef cls.uperEncFunction.func) | false -> None
                            let uPerDecFunc = match requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType) with true -> Some(combineStringOpts cls.uperDecFunction.funcDef cls.uperDecFunction.func) | false -> None

                            let xerEncFunc = match cls.xerEncFunction with XerFunction z -> Some(combineStringOpts z.funcDef z.func) | XerFunctionDummy -> None
                            let xerDecFunc = match cls.xerDecFunction with XerFunction z -> Some(combineStringOpts z.funcDef z.func) | XerFunctionDummy -> None

                            let hasAcnEncDec = r.callersSet |> Set.contains (f AcnEncDecFunctionType)
                            let acnEncFunc, sEncodingSizeConstant =
                                match hasAcnEncDec && requiresAcn, cls.acnEncFunction with
                                | true, Some x -> Some (combineStringOpts x.funcDef x.func), Some x.encodingSizeConstant
                                | _ -> None, None
                            let acnDecFunc =
                                match hasAcnEncDec && requiresAcn, cls.acnDecFunction with
                                | true, Some x -> Some(combineStringOpts x.funcDef x.func)
                                | _ -> None

                            let allProcs = [equal_funcs]@[is_valid_funcs]@special_init_funcs@[init_funcs]@([uPerEncFunc;uPerDecFunc;sEncodingSizeConstant; acnEncFunc; acnDecFunc;xerEncFunc;xerDecFunc] |> List.choose id)
                            lm.typeDef.Define_TAS type_definition allProcs
                        )
                )

            let arrsValues =
                vases |>
                List.map(fun gv -> printHeaderFileValueAssignment r pu.name lm gv)
            let arrsHeaderAnonymousValues =
                arrsAnonymousValues |>
                List.map(fun av -> lm.typeDef.PrintValueAssignment av.valueName av.typeDefinitionName "")


            let arrsPrototypes = []

            let sFileNameWithNoExtUpperCase = (ToC (System.IO.Path.GetFileNameWithoutExtension pu.specFileName))
            let bXer = r.args.encodings |> Seq.exists ((=) XER)
            let arrsUtilityDefines = []

            let definitionsContent =
                lm.typeDef.PrintSpecificationFile sFileNameWithNoExtUpperCase pu.name pu.importedProgramUnits typeDefs (arrsValues@arrsHeaderAnonymousValues) arrsPrototypes arrsUtilityDefines (not r.args.encodings.IsEmpty) bXer

            let fileName = Path.Combine(outDir, pu.specFileName)
            File.WriteAllText(fileName, definitionsContent.Replace("\r",""))
            File.AppendAllText(Path.Combine(outDir, "__init__.py"), $"import asn1pylib.asn1src.{pu.name}\n")

            // test cases file
            match r.args.generateAutomaticTestCases with
            | false -> ()
            | true  ->
                let typeDefs =
                    seq {
                        for tas in tases do
                            let typeAssignmentInfo = tas.Type.id.tasInfo.Value
                            let f cl = {Caller.typeId = typeAssignmentInfo; funcType = cl}
                            let reqUPER = r.callersSet |> Set.contains (f UperEncDecFunctionType)
                            let reqACN = r.callersSet |> Set.contains (f AcnEncDecFunctionType)

                            if reqUPER && r.args.encodings |> Seq.exists ((=) CommonTypes.UPER) then
                                yield (tas.Type.uperEncDecTestFunc |> Option.map (fun z -> (z.funcDef + "\n" + z.func)))
                            if r.args.encodings |> Seq.exists ((=) CommonTypes.XER) then
                                yield (tas.Type.xerEncDecTestFunc |> Option.map (fun z -> z.funcDef + "\n" + z.func))
                            if reqACN && r.args.encodings |> Seq.exists ((=) CommonTypes.ACN) then
                                yield (tas.Type.acnEncDecTestFunc |> Option.map (fun z -> z.funcDef + "\n" + z.func))
                        } |> Seq.choose id |> Seq.toList
                    
                let testcase_specFileName = Path.Combine(outDir, pu.testcase_specFileName)
                let tstCasesHdrContent = lm.atc.PrintAutomaticTestCasesBodyFile (ToC pu.testcase_specFileName) pu.name (pu.name::pu.importedProgramUnits) [""] typeDefs false
                File.WriteAllText(testcase_specFileName, tstCasesHdrContent.Replace("\r",""))
                
            definitionsContent, "BODY"    
        | _ ->
            //header file
            let typeDefs =
                tases |>
                List.map(fun tas ->
                    let typeAssignmentInfo = tas.Type.id.tasInfo.Value
                    let f cl = {Caller.typeId = typeAssignmentInfo; funcType = cl}

                    let type_definition =
                        match tas.Type.typeDefinitionOrReference with
                        | TypeDefinition td -> td.typedefBody ()
                        | ReferenceToExistingDefinition _   -> raise(BugErrorException "Type Assignment with no Type Definition")
                    let init_def        =
                        match r.callersSet |> Set.contains (f InitFunctionType) with
                        | true -> 
                            match lm.lg.initMethod with
                            | Procedure ->
                                Some(getInitializationFunctions tas.Type.initFunction |> List.choose( fun i_f -> i_f.initProcedure) |> List.map(fun c -> c.def) |> Seq.StrJoin "\n" )
                            | Function ->
                                Some(getInitializationFunctions tas.Type.initFunction |> List.choose( fun i_f -> i_f.initFunction) |> List.map(fun c -> c.def) |> Seq.StrJoin "\n" )
                        | false -> None

                    let init_globals    =
                        //we generate const globals only if requested by user and the init method is procedure
                        match r.args.generateConstInitGlobals && (lm.lg.initMethod  = Procedure) with
                        | false -> None
                        | true  -> Some (GetMySelfAndChildren tas.Type |> List.choose(fun t -> t.initFunction.initGlobal ) |> List.map(fun c -> c.def) |> Seq.StrJoin "\n")

                    let special_init_funcs =
                        tas.Type.initFunction.user_aux_functions |> List.map fst


                    let equal_defs =
                        match r.args.GenerateEqualFunctions && (r.callersSet |> Set.contains (f EqualFunctionType)) with
                        | true  -> GetMySelfAndChildren tas.Type |> List.choose(fun t -> t.equalFunction.isEqualFuncDef )
                        | false -> []
                    let isValidFuncs =
                        match r.callersSet |> Set.contains (f IsValidFunctionType) with
                        | false -> []
                        | true  ->
                            match tas.Type.isValidFunction with
                            | None      -> []
                            | Some f    ->
                                getValidFunctions f |> List.choose(fun f -> f.funcDef)


                    let uPerEncFunc = match requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType) with true -> tas.Type.uperEncFunction.funcDef | false -> None
                    let uPerDecFunc = match requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType) with true -> tas.Type.uperDecFunction.funcDef | false -> None

                    let xerEncFunc = match tas.Type.xerEncFunction with XerFunction z -> z.funcDef | XerFunctionDummy -> None
                    let xerDecFunc = match tas.Type.xerDecFunction with XerFunction z -> z.funcDef | XerFunctionDummy -> None

                    let hasAcnEncDec = r.callersSet |> Set.contains (f AcnEncDecFunctionType)
                    let acnEncFunc, sEncodingSizeConstant =
                        match hasAcnEncDec && requiresAcn, tas.Type.acnEncFunction with
                        | true, Some x -> x.funcDef, Some x.encodingSizeConstant
                        | _  -> None, None
                    let acnDecFunc =
                        match hasAcnEncDec && requiresAcn, tas.Type.acnDecFunction with
                        | true, Some x -> x.funcDef
                        | _ -> None

                    let allProcs = equal_defs@isValidFuncs@special_init_funcs@([init_globals;init_def;uPerEncFunc;uPerDecFunc;sEncodingSizeConstant; acnEncFunc; acnDecFunc;xerEncFunc;xerDecFunc] |> List.choose id)
                    lm.typeDef.Define_TAS type_definition allProcs
                )
            let arrsValues =
                vases |>
                List.map(fun gv -> printHeaderFileValueAssignment r pu.name lm gv)
            let arrsHeaderAnonymousValues =
                arrsAnonymousValues |>
                List.map(fun av -> lm.typeDef.PrintValueAssignment av.valueName av.typeDefinitionName "")


            let arrsPrototypes = []

            let sFileNameWithNoExtUpperCase = (ToC (System.IO.Path.GetFileNameWithoutExtension pu.specFileName))
            let bXer = r.args.encodings |> Seq.exists ((=) XER)
            let arrsUtilityDefines = []
            let puCorrName =
                match r.lang with
                | CommonTypes.ProgrammingLanguage.Scala -> ToC (pu.name)
                | _ -> pu.name

            let definitionsContntent =
                lm.typeDef.PrintSpecificationFile sFileNameWithNoExtUpperCase puCorrName pu.importedProgramUnits typeDefs (arrsValues@arrsHeaderAnonymousValues) arrsPrototypes arrsUtilityDefines (not r.args.encodings.IsEmpty) bXer

            let fileName = Path.Combine(outDir, pu.specFileName)
            File.WriteAllText(fileName, definitionsContntent.Replace("\r",""))


            // test cases header file
            match r.args.generateAutomaticTestCases with
            | false -> ()
            | true  ->
                let typeDefs =
                    seq {
                        for tas in tases do
                            let typeAssignmentInfo = tas.Type.id.tasInfo.Value
                            let f cl = {Caller.typeId = typeAssignmentInfo; funcType = cl}
                            let reqUPER = r.callersSet |> Set.contains (f UperEncDecFunctionType)
                            let reqACN = r.callersSet |> Set.contains (f AcnEncDecFunctionType)

                            if reqUPER && r.args.encodings |> Seq.exists ((=) CommonTypes.UPER) then
                                yield (tas.Type.uperEncDecTestFunc |> Option.map (fun z -> z.funcDef))
                            if r.args.encodings |> Seq.exists ((=) CommonTypes.XER) then
                                yield (tas.Type.xerEncDecTestFunc |> Option.map (fun z -> z.funcDef))
                            if reqACN && r.args.encodings |> Seq.exists ((=) CommonTypes.ACN) then
                                yield (tas.Type.acnEncDecTestFunc |> Option.map (fun z -> z.funcDef))
                        } |> Seq.choose id |> Seq.toList
                let testcase_specFileName = Path.Combine(outDir, pu.testcase_specFileName)
                let tstCasesHdrContent = lm.atc.PrintAutomaticTestCasesSpecFile (ToC pu.testcase_specFileName) pu.name (pu.name::pu.importedProgramUnits) typeDefs
                File.WriteAllText(testcase_specFileName, tstCasesHdrContent.Replace("\r",""))

            //source file
            let arrsTypeAssignments =
                tases |> List.map(fun t ->
                    let typeAssignmentInfo = t.Type.id.tasInfo.Value
                    let f cl = {Caller.typeId = typeAssignmentInfo; funcType = cl}

                    let privateDefinition =
                        match t.Type.typeDefinitionOrReference with
                        | TypeDefinition td -> td.privateTypeDefinition
                        | ReferenceToExistingDefinition _   -> None

                    let initialize =
                        match r.callersSet |> Set.contains (f InitFunctionType) with
                        | true -> 
                            match lm.lg.initMethod with
                            | InitMethod.Procedure  ->
                                Some(getInitializationFunctions t.Type.initFunction |> List.choose( fun i_f -> i_f.initProcedure) |> List.map(fun c -> c.body) |> Seq.StrJoin "\n" )
                            | InitMethod.Function  ->
                                Some(getInitializationFunctions t.Type.initFunction |> List.choose( fun i_f -> i_f.initFunction) |> List.map(fun c -> c.body) |> Seq.StrJoin "\n" )
                        | false -> None

                    let init_globals    =
                        match r.args.generateConstInitGlobals  && (lm.lg.initMethod  = Procedure) with
                        | false -> None
                        | true  -> Some (GetMySelfAndChildren t.Type |> List.choose(fun t -> t.initFunction.initGlobal) |> List.map(fun c -> c.body) |> Seq.StrJoin "\n")


                    let special_init_funcs =
                        t.Type.initFunction.user_aux_functions |> List.map snd

                    let eqFuncs =
                        match r.args.GenerateEqualFunctions && (r.callersSet |> Set.contains (f EqualFunctionType)) with
                        | true  -> GetMySelfAndChildren t.Type |> List.choose(fun y -> y.equalFunction.isEqualFunc)
                        | false -> []

                    let isValidFuncs =
                        match r.callersSet |> Set.contains (f IsValidFunctionType) with
                        | false -> []
                        | true  ->
                            match t.Type.isValidFunction with
                            | None      -> []
                            | Some f    ->
                                getValidFunctions f |> List.choose(fun f -> f.func)

                    let uperEncDec =
                        if requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType) then
                            ((t.Type.uperEncFunction.func |> Option.toList |> List.collect (fun f -> f :: t.Type.uperEncFunction.auxiliaries))) @
                            ((t.Type.uperDecFunction.func |> Option.toList |> List.collect (fun f ->  f :: t.Type.uperDecFunction.auxiliaries)))
                        else []

                    let xerEncDec =
                        (match t.Type.xerEncFunction with
                        | XerFunction z ->  z.func |> Option.toList
                        | XerFunctionDummy  -> []) @
                        (match t.Type.xerDecFunction with
                        | XerFunction z -> z.func |> Option.toList
                        | XerFunctionDummy -> [])
                    
                    let hasAcnEncDec = r.callersSet |> Set.contains (f AcnEncDecFunctionType)
                    let ancEncDec =
                        if requiresAcn && hasAcnEncDec then
                            (t.Type.acnEncFunction |> Option.toList |> List.collect (fun x -> (x.func |> Option.toList) @ x.auxiliaries)) @
                            (t.Type.acnDecFunction |> Option.toList |> List.collect (fun x -> (x.func |> Option.toList) @ x.auxiliaries))
                        else []
                    let allProcs =
                        (privateDefinition |> Option.toList) @
                        eqFuncs @ isValidFuncs @ special_init_funcs @
                        (init_globals |> Option.toList) @
                        (initialize |> Option.toList) @
                        uperEncDec @ ancEncDec @ xerEncDec
                    lm.src.printTass allProcs)


            let arrsValueAssignments, arrsSourceAnonymousValues =
                match lm.lg.requiresValueAssignmentsInSrcFile with
                | true ->
                    let arrsValueAssignments = vases |> List.map (printSourceFileValueAssignment r pu.name lm)
                    let arrsSourceAnonymousValues =  arrsAnonymousValues |> List.map (fun av -> lm.vars.PrintValueAssignment av.typeDefinitionName av.valueName av.valueExpression)
                    arrsValueAssignments, arrsSourceAnonymousValues
                | false ->
                    [], []
            let rtlFiles = lm.lg.getRtlFiles r.args.encodings arrsTypeAssignments
            let arrsImportedFiles = rtlFiles@pu.importedUserModules@pu.importedProgramUnits |> List.distinct
            let puCorrName =
                match r.lang with
                | CommonTypes.ProgrammingLanguage.Scala -> ToC (pu.name)
                | _ -> pu.name
            let srcBody = lm.src.printSourceFile puCorrName arrsImportedFiles pu.importedTypes (arrsValueAssignments@arrsSourceAnonymousValues@arrsTypeAssignments)

            let eqContntent =
                match lm.lg.allowsSrcFilesWithNoFunctions with
                | true     ->
                    Some srcBody
                | false   ->
                    match arrsTypeAssignments with
                    | []    -> None
                    | _     -> Some srcBody

            match eqContntent with
            | Some eqContntent ->
                let fileName = Path.Combine(outDir, pu.bodyFileName) // todo: here
                match r.lang with
                // In case of Python, there is no Spec and Body file distinction, therefore we append rather than overwrite
                | CommonTypes.ProgrammingLanguage.Python -> File.AppendAllText(fileName, eqContntent.Replace("\r",""))
                | _ -> File.WriteAllText(fileName, eqContntent.Replace("\r",""))
            | None             -> ()

            //test cases source file
            match r.args.generateAutomaticTestCases with
            | false -> ()
            | true  ->
                let encDecFuncs =
                    seq {
                        for tas in tases do
                            let typeAssignmentInfo = tas.Type.id.tasInfo.Value
                            let f cl = {Caller.typeId = typeAssignmentInfo; funcType = cl}
                            let reqUPER = 
                                r.args.encodings |> Seq.exists ((=) CommonTypes.UPER)
                                && r.callersSet |> Set.contains (f UperEncDecFunctionType)
                            let reqACN = 
                                r.args.encodings |> Seq.exists ((=) CommonTypes.ACN)
                                && r.callersSet |> Set.contains (f AcnEncDecFunctionType)

                            if reqUPER then
                                yield (tas.Type.uperEncDecTestFunc |> Option.map (fun z -> z.func))
                            if r.args.encodings |> Seq.exists ((=) CommonTypes.XER) then
                                yield (tas.Type.xerEncDecTestFunc |> Option.map (fun z -> z.func))
                            if reqACN  then
                                yield (tas.Type.acnEncDecTestFunc |> Option.map (fun z -> z.func))
                        } |> Seq.choose id |> Seq.toList

                let testcase_SrcFileName = Path.Combine(outDir, pu.testcase_bodyFileName)
                let bXer = r.args.encodings |> Seq.exists((=) XER)
                let tstCasesHdrContent =
                    match lm.lg.allowsSrcFilesWithNoFunctions with
                    | true     -> Some (lm.atc.PrintAutomaticTestCasesBodyFile pu.name pu.testcase_specFileName pu.importedProgramUnits [] encDecFuncs bXer)
                    | false   ->
                        match encDecFuncs with
                        | []    -> None
                        | _     -> Some (lm.atc.PrintAutomaticTestCasesBodyFile pu.name pu.testcase_specFileName pu.importedProgramUnits [] encDecFuncs bXer)

                tstCasesHdrContent |> Option.iter(fun tstCasesHdrContent -> File.WriteAllText(testcase_SrcFileName, tstCasesHdrContent.Replace("\r","")))
            (definitionsContntent, srcBody)
        
    (definitionsContntent, srcBody)



let generateAll (di:DirInfo) (r:DAst.AstRoot)  (lm:LanguageMacros) (encodings: CommonTypes.Asn1Encoding list)  =
    let _ = match r.lang with
            | Python ->
                // Write basic __init__.py in root & in srcDir
                File.WriteAllLines(Path.Combine(di.rootDir, "__init__.py"), ["from .asn1python import *"] @ ["from .asn1src import *"])
                File.WriteAllText(Path.Combine(di.srcDir, "__init__.py"), "")
            | l -> ignore l
    
    let generatedContent = r.programUnits |> List.map(printUnit r lm encodings di.srcDir) |> List.map snd |> Seq.StrJoin "\n"
    match r.args.generateAutomaticTestCases with
    | false -> ()
    | true  ->
        lm.lg.CreateMakeFile r di
        let arrsSrcTstFiles, arrsHdrTstFiles = DastTestCaseCreation.printAllTestCasesAndTestCaseRunner r lm di.srcDir
        lm.lg.CreateAuxFiles r di (arrsSrcTstFiles, arrsHdrTstFiles)
    generatedContent


let EmitDefaultACNGrammar (r:AstRoot) outDir  =
    let printTas (tas: TypeAssignment) =
        tas.Name.Value + "[]"
    let printModule (m:Asn1Module) =
        let arrTases = m.TypeAssignments |> Seq.map printTas
        stg_acn.PrintDefaultAcnModule m.Name.Value arrTases "::="
    let printFile (f:Asn1File) =
        let fileName = f.FileNameWithoutExtension + ".acn"
        if (System.IO.File.Exists fileName) then
            System.Console.Error.WriteLine("File {0} already exists. Creation of default ASN.1 grammar abandoned", fileName);
        else
            let content = f.Modules |> Seq.map printModule |> Seq.StrJoin "\n"
            let fileName = Path.Combine(outDir, fileName)
            File.WriteAllText(fileName, content.Replace("\r",""))

    r.Files |> Seq.iter printFile