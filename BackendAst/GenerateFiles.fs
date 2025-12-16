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

/// Gets the actual resolved type of any Asn1Type recursively, following references and collecting all children
let rec getResolvedTypeAndChildren (t:Asn1Type) : Asn1Type list =
    [
        // Yield the current type (might be a reference or actual type)
        yield t

        // Recursively process children based on kind
        match t.Kind with
        | SequenceOf o ->
            yield! getResolvedTypeAndChildren o.childType
        | Sequence o   ->
            for ch in o.Asn1Children do
                yield! getResolvedTypeAndChildren ch.Type
        | Choice o ->
            for ch in o.children do
                yield! getResolvedTypeAndChildren ch.chType
        | ReferenceType rt ->
            // Follow the reference and get the resolved type
            // This resolved type will have the ACN context from where it's used
            yield! getResolvedTypeAndChildren rt.resolvedType
        | _ -> ()
    ]


let private combineStringOpts(a: string option) (b: string option) = (defaultArg a "") + "\n" + (defaultArg b "")

let private printUnitInternal (tas: TypeAssignment) (fullCls: Asn1Type) (encDecCls: Asn1Type) (lm: LanguageMacros) (printInit: bool) (printEquals: bool) (printIsValid: bool) (printUper: bool) (printAcn: bool) =
    let type_definition =
        match fullCls.typeDefinitionOrReference with
        | TypeDefinition td -> td.typedefBodyOnly ()
        | ReferenceToExistingDefinition _ -> raise(BugErrorException "Type Assignment with no Type Definition")

    let init_funcs        =
        match printInit with
        | true -> match fullCls.initFunction.initProcedure with | Some k -> k.body | None -> ""
        | false -> ""

    // todo: do we need special init funcs? how can they look like?
    let special_init_funcs =
        fullCls.initFunction.user_aux_functions |> List.map fst

    let equal_funcs =
        match printEquals with
        | true  -> combineStringOpts fullCls.equalFunction.isEqualFuncDef fullCls.equalFunction.isEqualFunc
        | false -> ""

    let is_valid_funcs =
        match printIsValid with
        | false -> ""
        | true  ->
            match fullCls.isValidFunction with
            | None      -> ""
            | Some f    -> combineStringOpts f.funcDef f.func

    let uPerEncFunc = match printUper with true -> Some(combineStringOpts encDecCls.uperEncFunction.funcDef encDecCls.uperEncFunction.func) | false -> None
    let uPerDecFunc = match printUper with true -> Some(combineStringOpts encDecCls.uperDecFunction.funcDef encDecCls.uperDecFunction.func) | false -> None

    let xerEncFunc = match encDecCls.xerEncFunction with XerFunction z -> Some(combineStringOpts z.funcDef z.func) | XerFunctionDummy -> None
    let xerDecFunc = match encDecCls.xerDecFunction with XerFunction z -> Some(combineStringOpts z.funcDef z.func) | XerFunctionDummy -> None

    let acnEncFunc, sEncodingSizeConstant =
        match printAcn, encDecCls.acnEncFunction with
        | true, Some x -> Some (combineStringOpts x.funcDef x.func), Some x.encodingSizeConstant
        | _  -> None, None
    let acnDecFunc =
        match printAcn, encDecCls.acnDecFunction with
        | true, Some x -> Some(combineStringOpts x.funcDef x.func)
        | _ -> None

    let allProcs = [equal_funcs]@[is_valid_funcs]@special_init_funcs@[init_funcs]@([uPerEncFunc;uPerDecFunc;sEncodingSizeConstant; acnEncFunc; acnDecFunc;xerEncFunc;xerDecFunc] |> List.choose id)
    let generatedCode = lm.typeDef.Define_TAS type_definition allProcs
    generatedCode

let private printUnit (r:DAst.AstRoot)  (lm:LanguageMacros) (encodings: CommonTypes.Asn1Encoding list) outDir (pu:ProgramUnit)  =
    let tases = pu.sortedTypeAssignments
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
            let typeHasDeepFieldAccess (t: Asn1Type) : bool =
                getResolvedTypeAndChildren t
                |> List.exists (fun typ ->
                    match typ.Kind with
                    | Sequence seq ->
                        // Check if this sequence has ACN children with presence dependencies
                        seq.children |> List.exists (function
                            | AcnChild cld -> cld.deps.acnDependencies
                                              |> List.filter(function dep -> dep.dependencyKind.IsAcnDepPresence)
                                              |> List.isEmpty
                                              |> not
                            | _ -> false
                        )
                    | _ -> false
                )

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
                            let allChildrenRaw = getResolvedTypeAndChildren tas.Type

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
                            // Group by canonical type name using tasInfo when available
                            // This groups together the same logical type from different contexts
                            match t.tasInfo with
                            | Some ti -> $"{ti.modName}.{ti.tasName}"
                            | None -> t.id.AsString  // Fallback to full path if no tasInfo
                        )
                        |> List.map (fun (typeKey, tasTypePairs) ->
                            // Pick the "richest" version - the one with more children in its Sequence
                            // This ensures we get types with inline ACN children from parent context
                            let chosen = tasTypePairs |> List.maxBy (fun (tas, t) ->
                                match t.Kind with
                                | Sequence seq -> seq.children.Length
                                | _ -> 0
                            )
                            (typeKey, chosen)
                        )

                    // Generate code for each unique type (with correct ACN context)
                    // and store with multiple keys for flexible lookup
                    let mapEntries =
                        deduplicatedTypes |> List.collect(fun (canonicalKey, (parentTas, encDecCls)) ->
                            // DEBUG: Print what we're generating in STEP 1
                            printfn "[STEP 1] Generating for key: %s" canonicalKey
                            printfn "  encDecCls.id.AsString: %s" encDecCls.id.AsString
                            printfn "  encDecCls.id.tasInfo: %A" encDecCls.id.tasInfo
                            printfn "  parentTas: %s" (match parentTas.Type.id.tasInfo with Some ti -> $"{ti.modName}.{ti.tasName}" | None -> "None")

                            // Find the correct TAS for this type using the canonicalKey
                            // This ensures each type gets its own class name, not the parent's
                            // The canonicalKey is in format "ModuleName.TypeName"
                            let correctTas =
                                let parts = canonicalKey.Split('.')
                                if parts.Length >= 2 then
                                    let modName = parts.[0]
                                    let tasName = parts.[parts.Length - 1]  // Last part is the TAS name
                                    printfn "  Looking for TAS: %s.%s (from canonicalKey)" modName tasName

                                    let found = tases |> List.tryFind (fun tas ->
                                        match tas.Type.id.tasInfo with
                                        | Some ti ->
                                            let matches = ti.modName = modName && ti.tasName = tasName
                                            if matches then printfn "    FOUND matching TAS: %s.%s" ti.modName ti.tasName
                                            matches
                                        | None -> false
                                    )

                                    match found with
                                    | Some tas ->
                                        printfn "  Using correctTas: %s.%s" modName tasName
                                        tas
                                    | None ->
                                        printfn "  NOT FOUND - falling back to parentTas"
                                        parentTas
                                else
                                    printfn "  Invalid canonicalKey format - using parentTas"
                                    parentTas

                            let f cl = {Caller.typeId = correctTas.Type.id.tasInfo.Value; funcType = cl}
                            let printInit = r.callersSet |> Set.contains (f InitFunctionType)
                            let printEquals = r.args.GenerateEqualFunctions && (r.callersSet |> Set.contains (f EqualFunctionType))
                            let printIsValid = r.callersSet |> Set.contains (f IsValidFunctionType)
                            let printUper = requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType)
                            let printAcn = requiresAcn && r.callersSet |> Set.contains (f AcnEncDecFunctionType)

                            let isFullDefinition, fullCls  =
                                match encDecCls.typeDefinitionOrReference with
                                | TypeDefinition td ->
                                    true, correctTas.Type
                                | ReferenceToExistingDefinition ref ->
                                    let myTas = tasesNeedingDeepFieldAccess |> List.filter(fun tas -> ToC tas.python_name = ToC ref.typedefName)
                                    if myTas.Length = 0 then
                                        false, correctTas.Type
                                    else
                                        let myTas = myTas |> List.head
                                        false, myTas.Type


                            let typeDef = printUnitInternal correctTas fullCls encDecCls lm printInit printEquals printIsValid printUper printAcn

                            // Store with multiple keys so it can be looked up flexibly:
                            // 1. Full scope path from encDecCls
                            // 2. Canonical name (modName.tasName) if available
                            // This allows lookup from different contexts
                            // Also store the canonicalKey so we can identify which TAS this type belongs to
                            let keys =
                                [
                                    encDecCls.id.AsString  // Full path
                                    canonicalKey           // Canonical name
                                ] |> List.distinct

                            keys |> List.map (fun key -> (key, (typeDef, canonicalKey)))
                        )

                    mapEntries |> Map.ofList

            // STEP 2: Process tases in original order, using map for deep field access types
            let tryFindInMap (t: Asn1Type) =
                // Try multiple key strategies to find the type
                let canonicalKey =
                    match t.tasInfo with
                    | Some ti -> Some $"{ti.modName}.{ti.tasName}"  // Canonical name
                    | None -> None

                let possibleKeys = [Some t.id.AsString; canonicalKey] |> List.choose id

                possibleKeys
                |> List.tryPick (fun key ->
                    if deepFieldAccessMap.ContainsKey(key) then
                        Some (deepFieldAccessMap.[key])
                    else
                        None
                )

            let typeDefs =
                tases |> List.collect(fun tas ->
                    // DEBUG: Print what we're processing
                    printfn "=== Processing TAS: %s ===" (match tas.Type.id.tasInfo with Some ti -> $"{ti.modName}.{ti.tasName}" | None -> tas.Type.id.AsString)

                    // Get all children (including the type itself) with resolved references
                    // Use same filtering logic as STEP 1 to ensure consistency
                    let allChildren = getResolvedTypeAndChildren tas.Type
                                      |> List.filter (fun t ->
                                          match t.typeDefinitionOrReference.IsTypeDefinition, t.Kind with
                                          | true, _ -> true  // Keep all types with TypeDefinition
                                          | false, Sequence _ -> true  // Keep resolved Sequences
                                          | false, SequenceOf _ -> true  // Keep resolved SequenceOfs
                                          | false, Choice _ -> true    // Keep resolved Choices
                                          | false, _ -> false  // Skip everything else (primitives, references)
                                      )

                    printfn "  All children: %A" (allChildren |> List.map (fun t -> match t.id.tasInfo with Some ti -> $"{ti.modName}.{ti.tasName}" | None -> t.id.AsString))

                    // Separate children into those with deep field access (in map) and those without
                    let childrenInMap, childrenNotInMap =
                        allChildren |> List.partition (fun t -> tryFindInMap t |> Option.isSome)

                    printfn "  Children in map: %A" (childrenInMap |> List.map (fun t -> match t.id.tasInfo with Some ti -> $"{ti.modName}.{ti.tasName}" | None -> t.id.AsString))
                    printfn "  Children NOT in map: %A" (childrenNotInMap |> List.map (fun t -> match t.id.tasInfo with Some ti -> $"{ti.modName}.{ti.tasName}" | None -> t.id.AsString))

                    // Filter childrenInMap to exclude types that have their own top-level TAS
                    // (they'll be generated when processing their own TAS, not as children)
                    let childrenInMapToGenerate =
                        childrenInMap |> List.filter (fun child ->
                            // Get the canonicalKey for this child from the map
                            match tryFindInMap child with
                            | Some (_, childCanonicalKey) ->
                                match tas.Type.id.tasInfo with
                                | Some tasInfo ->
                                    let currentTasCanonicalKey = $"{tasInfo.modName}.{tasInfo.tasName}"
                                    // Is this the TAS itself?
                                    if childCanonicalKey = currentTasCanonicalKey then
                                        true  // It's the TAS itself, include it
                                    else
                                        // It's a different type - check if it has its own TAS
                                        // Parse canonicalKey to extract modName and tasName
                                        let parts = childCanonicalKey.Split('.')
                                        if parts.Length >= 2 then
                                            let modName = parts.[0]
                                            let tasName = parts.[parts.Length - 1]
                                            let hasOwnTas = tases |> List.exists (fun otherTas ->
                                                match otherTas.Type.id.tasInfo with
                                                | Some otherInfo ->
                                                    otherInfo.modName = modName && otherInfo.tasName = tasName
                                                | None -> false
                                            )
                                            not hasOwnTas  // Exclude if it has its own TAS
                                        else
                                            true  // Can't parse, include it
                                | None -> true  // Current TAS has no tasInfo, include child
                            | None -> false  // Not in map, shouldn't happen here but exclude for safety
                        )

                    printfn "  Children to generate from map: %A" (childrenInMapToGenerate |> List.map (fun t -> match t.id.tasInfo with Some ti -> $"{ti.modName}.{ti.tasName}" | None -> t.id.AsString))

                    // For types in the map, use the pre-generated code (with correct ACN context)
                    let typeDefsFromMap =
                        childrenInMapToGenerate |> List.choose (fun child ->
                            tryFindInMap child |> Option.map fst  // Extract just the typeDef, not the canonicalKey
                        )

                    // For types not in the map, generate code normally
                    let typeAssignmentInfo = tas.Type.id.tasInfo.Value
                    let f cl = {Caller.typeId = typeAssignmentInfo; funcType = cl}

                    let typeDefsGenerated =
                        childrenNotInMap |> List.map(fun cls ->
                            let printInit = r.callersSet |> Set.contains (f InitFunctionType)
                            let printEquals = r.args.GenerateEqualFunctions && (r.callersSet |> Set.contains (f EqualFunctionType))
                            let printIsValid = r.callersSet |> Set.contains (f IsValidFunctionType)
                            let printUper = requiresUPER && r.callersSet |> Set.contains (f UperEncDecFunctionType)
                            let printAcn = requiresAcn && r.callersSet |> Set.contains (f AcnEncDecFunctionType)
                            printfn "    Generating code for: %s" (match cls.id.tasInfo with Some ti -> $"{ti.modName}.{ti.tasName}" | None -> cls.id.AsString)
                            printUnitInternal tas cls cls lm printInit printEquals printIsValid printUper printAcn
                        )

                    // Return both: types from map + freshly generated types
                    // Order matters: children before parents (types are already in correct order from getResolvedTypeAndChildren)
                    typeDefsFromMap @ typeDefsGenerated
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