module ProofGen_python

open System.Numerics
open DAst
open DAstUtilFunctions
open FsUtils
open CommonTypes
open Language
open Asn1AcnAst
open Asn1AcnAstUtilFunctions
open verification_python

let Ensures (expr: string): string = $"Ensures({expr})"

let fieldOldEqual (fieldName: string): string =
    Ensures $"Unfolding(Acc(self.class_predicate(), 1/20), {fieldName}) ==
            Old(Unfolding(Acc(self.class_predicate(), 1/20), {fieldName}))"


let getFieldsPostcond (r: Asn1AcnAst.AstRoot) (t: Asn1AcnAst.Asn1Type) (lg: ILangGeneric) (objectRef: string): string list =
    match t.Kind with
    | OctetString _ -> 
        [
            fieldOldEqual "ToSeq(self.arr)"
        ]
    | _ -> []

let generateIsValidPrecond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (lg: ILangGeneric): string list =
    [
        "Acc(self.class_predicate(), 1/20)"
    ]

let generateIsValidPostcond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (lg: ILangGeneric): string list =
    [Ensures "Acc(self.class_predicate(), 1/20)"] @
    getFieldsPostcond r t lg "self" @
    [
        
        Ensures"Implies(self.is_constraint_valid_pure(), ResultT(Asn1ConstraintValidResult).is_valid)";
        Ensures"Implies(ResultT(Asn1ConstraintValidResult).is_valid, ResultT(Asn1ConstraintValidResult).error_code == 0 and ResultT(Asn1ConstraintValidResult).message == '')";
        Ensures "Implies(not ResultT(Asn1ConstraintValidResult).is_valid, ResultT(Asn1ConstraintValidResult).error_code != 0)"
    ]

let generatePrecond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (codec: Codec) (lg: ILangGeneric): string list =
    let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]

    match codec with
    | Encode ->
        [
            "Acc(self.class_predicate(), 1/20)";
            "codec.codec_predicate() and codec.write_invariant()";
            "codec.remaining_bits >= " + string(t.maxSizeInBits enc);
            "check_constraints and self.is_constraint_valid_pure()"
        ]
    | Decode ->
        [
            "codec.codec_predicate() and codec.read_invariant()";
            $"{typeName}.segments_valid(segments_drop(codec.segments, codec.segments_read_index))";
            $"codec.segments_read_index + {typeName}.segments_count(segments_drop(codec.segments, codec.segments_read_index)) 
            <= len(codec.segments)"
        ]

let generatePostcond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (p: CodegenScope) (t: Asn1AcnAst.Asn1Type) (codec: Codec) (lg: ILangGeneric): string list =
    let usedBits = t.maxSizeInBits enc
    let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]

    match codec with
    | Encode ->
        ["Ensures(Acc(self.class_predicate(), 1/20))"] @
        getFieldsPostcond r t lg "self" @
        [
            "Ensures(codec.codec_predicate() and codec.write_invariant())";
            "Ensures(codec.buffer_size == Old(codec.buffer_size))";
            $"Ensures(codec.segments is Old(codec.segments) + {typeName}.segments_of(self))"
        ]
    | Decode ->
        [   
            Ensures "codec.codec_predicate() and codec.read_invariant()";
            Ensures "codec.segments is Old(codec.segments) and codec.buffer == Old(codec.buffer)";
            $"Ensures(codec.bit_index == Old(codec.bit_index) + {usedBits})";
            $"Ensures(codec.segments_read_index == Old(codec.segments_read_index) +
            {typeName}.segments_count(Old(segments_drop(codec.segments, codec.segments_read_index))))"
            $"Ensures(Acc(ResultT({typeName}).class_predicate()) and ResultT({typeName}).is_constraint_valid_pure())";
            $"Ensures({typeName}.segments_of(ResultT({typeName})) ==
            segments_take(segments_drop(codec.segments, Old(codec.segments_read_index)), {typeName}.segments_count(segments_drop(codec.segments, Old(codec.segments_read_index)))))";
        ]
let rec isPrimitiveType (t: Asn1AcnAst.Asn1Type): bool =
    match t.Kind with
    | Integer _ | Boolean _ | Real _ | NullType _  ->
        match t.typeDefinitionOrReference.[Python] with
        | ReferenceToExistingDefinition _ -> true
        | TypeDefinition _ -> false
    | _ -> false

//#region Auxiliaries
//#region Sequence

let generateSequenceChildHelper (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child) (func: (string -> string -> bool -> BigInteger -> string)): string =
    let childName = child._python_name
    // Get the type name using the proper method
    let asn1Type: Asn1AcnAst.Asn1Type = child.Type
    let typeDefOrRef: TypeDefinitionOrReference = asn1Type.typeDefinitionOrReference.[Python]
    let childTypeDef: string = typeDefOrRef.longTypedefName2 (Some lg) lg.hasModules moduleName
    
    let childTypeName =
        if lg.hasModules = false && childTypeDef.StartsWith((ToC moduleName) + ".") then
            childTypeDef.Substring(moduleName.Length + 1)
        else
            childTypeDef
    let bIsPrimitive = isPrimitiveType child.Type
    let bitSize = child.maxSizeInBits enc

    func childName childTypeName bIsPrimitive bitSize

let generateSequenceChildSegmentsValid (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> segments_valid_child_sequenceof childName childTypeName bIsPrimitive bitSize
        | Choice _ -> segments_valid_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> segments_valid_child_optional childName childTypeName bIsPrimitive bitSize
            | None -> segments_valid_child_mandatory childName childTypeName bIsPrimitive bitSize
    generateSequenceChildHelper lg enc moduleName child func

let generateSequenceChildSegmentCollection (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> segments_of_child_sequenceof childName childTypeName bIsPrimitive bitSize
        | Choice _ -> segments_of_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> segments_of_child_optional childName childTypeName bIsPrimitive bitSize
            | None -> segments_of_child_mandatory childName childTypeName bIsPrimitive bitSize
    generateSequenceChildHelper lg enc moduleName child func

let generateSequenceChildSegmentsCount (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> segments_count_child_sequenceof childName childTypeName bIsPrimitive bitSize
        | Choice _ -> segments_count_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> segments_count_child_optional childName childTypeName bIsPrimitive bitSize
            | None -> segments_count_child_mandatory childName childTypeName bIsPrimitive bitSize
    generateSequenceChildHelper lg enc moduleName child func

let generateSequenceChildSegmentsEqLemma (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> segments_eq_lemma_child_sequenceof childName childTypeName bIsPrimitive bitSize
        | Choice _ -> segments_eq_lemma_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> segments_eq_lemma_child_optional childName childTypeName bIsPrimitive bitSize
            | None -> segments_eq_lemma_child_mandatory childName childTypeName bIsPrimitive bitSize
    generateSequenceChildHelper lg enc moduleName child func 

let generateSequenceAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (sq: Asn1AcnAst.Sequence) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    match codec with
    | Decode ->
        let typeName = (lg.getSequenceTypeDefinition sq.typeDef).typeName

        let asn1Children =
            sq.children |> List.choose (function
                | Asn1Child ch -> Some ch
                | _ -> None)

        let childSegmentsValid =
            asn1Children |> List.map (generateSequenceChildSegmentsValid lg enc t.moduleName)
        let childSegments =
            asn1Children |> List.map (generateSequenceChildSegmentCollection lg enc t.moduleName)
        let childSegmentsCount =
            asn1Children |> List.map (generateSequenceChildSegmentsCount lg enc t.moduleName)
        let childSegmentsEqLemma =
            asn1Children |> List.map (generateSequenceChildSegmentsEqLemma lg enc t.moduleName)

        // Generate functions using templates
        let classPredicateFunc = class_predicate_fields []
        let segmentsValidFunc = segments_valid_sequence typeName childSegmentsValid
        let segmentsCountFunc = segments_count_sequence typeName childSegmentsCount
        let segmentsOfFunc = segments_of_sequence typeName childSegments
        let segmentsEqLemma = segments_eq_lemma_sequence typeName childSegmentsEqLemma

        [classPredicateFunc; segmentsValidFunc; segmentsCountFunc; segmentsOfFunc; segmentsEqLemma]
    | _ -> []

//#endregion
let getChoiceChildTypeName (lg: ILangGeneric) (moduleName: string) (child: Asn1AcnAst.ChChildInfo): string =
    let typeDefOrRef: TypeDefinitionOrReference = child.Type.typeDefinitionOrReference.[Python]
    let childTypeDef: string = typeDefOrRef.longTypedefName2 (Some lg) lg.hasModules moduleName
    if lg.hasModules = false && childTypeDef.StartsWith((ToC moduleName) + ".") then
        childTypeDef.Substring(moduleName.Length + 1)
    else
        childTypeDef

let uperChoiceTagBitSize (n: int): BigInteger =
    if n <= 1 then BigInteger.Zero
    else
        let rec countBits bits v = if v = 0 then bits else countBits (bits + 1) (v >>> 1)
        BigInteger (countBits 0 (n - 1))

let generateChoiceAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (ch: Asn1AcnAst.Choice) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    match codec, sel.steps.IsEmpty with
    | Decode, true ->
        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let nChildren = ch.children |> List.length
        let tagBitSize = uperChoiceTagBitSize nChildren

        let childPredicates  = 
            ch.children |> List.map (fun child ->
                let childTypeName = getChoiceChildTypeName lg t.moduleName child
                let bIsPrimitive = isPrimitiveType child.Type
                class_predicate_choice_child childTypeName bIsPrimitive
            )

        let childSegmentsValid =
            ch.children |> List.mapi (fun i child ->
                let childTypeName = getChoiceChildTypeName lg t.moduleName child
                let bIsPrimitive = isPrimitiveType child.Type
                let dataBitSize = child.Type.maxSizeInBits enc
                segments_valid_choice_child (BigInteger i) childTypeName bIsPrimitive dataBitSize tagBitSize)

        let childSegmentsOf =
            ch.children |> List.mapi (fun i child ->
                let presentWhenName = lg.getChoiceChildPresentWhenName ch child t.moduleName
                let childTypeName = getChoiceChildTypeName lg t.moduleName child
                let bIsPrimitive = isPrimitiveType child.Type
                let dataBitSize = child.Type.maxSizeInBits enc
                segments_of_choice_child presentWhenName (BigInteger i) childTypeName bIsPrimitive dataBitSize tagBitSize)

        let childSegmentsCount =
            ch.children |> List.mapi (fun i child ->
                let childTypeName = getChoiceChildTypeName lg t.moduleName child
                let bIsPrimitive = isPrimitiveType child.Type
                segments_count_choice_child (BigInteger i) childTypeName bIsPrimitive)

        let childSegmentsEqLemma =
            ch.children |> List.mapi (fun i child ->
                let presentWhenName = lg.getChoiceChildPresentWhenName ch child t.moduleName
                let childTypeName = getChoiceChildTypeName lg t.moduleName child
                let bIsPrimitive = isPrimitiveType child.Type
                segments_eq_lemma_choice_child presentWhenName childTypeName bIsPrimitive)

        let classPredicateFunc = class_predicate_choice childPredicates
        let segmentsValidFunc = segments_valid_choice typeName childSegmentsValid
        let segmentsCountFunc = segments_count_choice typeName childSegmentsCount
        let segmentsOfFunc = segments_of_choice typeName childSegmentsOf
        let segmentsEqLemma = segments_eq_lemma_choice typeName childSegmentsEqLemma

        ["# CHOICE AUX"; classPredicateFunc; segmentsValidFunc; segmentsCountFunc; segmentsOfFunc; segmentsEqLemma]
    | _, _ -> ["# Choice AUX (unused)"]

let generateIntegerAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (int: Asn1AcnAst.Integer) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let bitSize = t.maxSizeInBits enc
    match codec, sel.steps.IsEmpty with
    | Decode, true ->

        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let classPredicateFunc = class_predicate_fields []
        let segmentsValidFunc = segments_valid_primitive typeName bitSize
        let segmentsCountFunc = segments_count_primitive typeName ((bitSize / BigInteger 32 + BigInteger 1).ToString())
        let segmentsOfFunc = segments_of_primitive typeName bitSize
        let segmentsEqLemma = segments_eq_lemma_primitive typeName bitSize

        ["# INTEGER AUX"; classPredicateFunc; segmentsValidFunc; segmentsCountFunc; segmentsOfFunc; segmentsEqLemma]
    | _, _ -> ["# Integer AUX (unused)"]

let generateBooleanAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (boolean: Asn1AcnAst.Boolean) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let bitSize = t.maxSizeInBits enc
    match codec, sel.steps.IsEmpty with
    | Decode, true ->

        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let classPredicateFunc = class_predicate_fields []
        let segmentsValidFunc = segments_valid_primitive typeName bitSize
        let segmentsCountFunc = segments_count_primitive typeName "1"
        let segmentsOfFunc = segments_of_boolean typeName bitSize
        let segmentsEqLemma = segments_eq_lemma_boolean typeName bitSize

        ["# BOOLEAN AUX"; classPredicateFunc; segmentsValidFunc; segmentsCountFunc; segmentsOfFunc; segmentsEqLemma]
    | _, _ -> ["# Boolean AUX (unused)"]

let generateNullTypeAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (nt: Asn1AcnAst.NullType) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let bitSize = t.maxSizeInBits enc
    match codec, sel.steps.IsEmpty with
    | Decode, true ->

        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let classPredicateFunc = class_predicate_fields []
        let segmentsValidFunc = segments_valid_primitive typeName bitSize
        let segmentsCountFunc = segments_count_primitive typeName "1"
        let segmentsOfFunc = segments_of_nulltype typeName bitSize
        let segmentsEqLemma = segments_eq_lemma_primitive typeName bitSize

        ["# NULLTYPE AUX"; classPredicateFunc; segmentsValidFunc; segmentsCountFunc; segmentsOfFunc; segmentsEqLemma]
    | _, _ -> ["# NullType AUX (unused)"]

let generateEnumAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (enm: Asn1AcnAst.Enumerated) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let bitSize = t.maxSizeInBits enc
    match codec, sel.steps.IsEmpty with
    | Decode, true ->

        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let classPredicateFunc = class_predicate_fields []
        let segmentsValidFunc = segments_valid_primitive typeName bitSize
        let segmentsCountFunc = segments_count_primitive typeName "1"
        let segmentsOfFunc = segments_of_enum typeName bitSize
        let segmentsEqLemma = segments_eq_lemma_enum typeName bitSize

        ["# ENUM AUX"; classPredicateFunc; segmentsValidFunc; segmentsCountFunc; segmentsOfFunc; segmentsEqLemma]
    | _, _ -> ["# Enum AUX (unused)"]

let generateOctetStringAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (os: Asn1AcnAst.OctetString) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    match codec, sel.steps.IsEmpty with
    | Decode, true ->
        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        match os.isFixedSize with
        | true ->
            let minChildCount = os.minSize.uper
            let maxChildCount = os.maxSize.uper
            let classPredicateFunc = class_predicate_fields [list_perm_access "arr"]
            let segmentsValidFunc = segments_valid_sequenceOf typeName minChildCount maxChildCount os.isFixedSize true true (BigInteger 8) (BigInteger 8)
            let segmentsCountFunc = segments_count_primitive typeName (maxChildCount.ToString())
            let segmentsOfFunc = segments_of_octetString typeName "arr"
            let segmentsEqLemma = segments_eq_octetString typeName "arr"
            ["# OctetString AUX"; classPredicateFunc; segmentsValidFunc; segmentsCountFunc; segmentsOfFunc; segmentsEqLemma]

        | false ->
            // let segmentsCountFunc = segments_count_var_size typeName

            ["# OctetString AUX Var Size"]
    | _, _ -> ["# OctetString AUX (unused)"]

let generateBitStringAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (ch: Asn1AcnAst.BitString) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    ["# BitString AUX"]

let generateSequenceOfLikeAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (o: SequenceOfLike) (pg: SequenceOfLikeProofGen) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list * string option =
    match codec, sel.steps.IsEmpty with
    | Decode, true ->
        let typeName = lg.getLongTypedefName (o.definitionOrRef Python)
        let isChildPrimitive = 
            match o with
            | SqOf sqf -> isPrimitiveType sqf.child
            | StrType _ -> true

        let childMinCount = o.minNbElems enc
        let childMaxCount = o.maxNbElems enc
        let childMinSize = o.minElemSizeInBits enc
        let childMaxSize = o.maxElemSizeInBits enc
        // Apparently some types report elemFixedSize as False even though minSize == maxSize
        let childFixedSize = o.elemFixedSize || (childMinSize = childMaxSize)

        let classPredicateFunc = class_predicate_fields [list_perm_access "arr"]
        let segmentsValidFunc = segments_valid_sequenceOf typeName childMinCount childMaxCount o.isFixedSize isChildPrimitive childFixedSize childMinSize childMaxSize
        let segmentsCountFunc = segments_count_sequenceOf typeName childMinCount childMaxCount o.isFixedSize isChildPrimitive childFixedSize childMinSize childMaxSize
        let segmentsOfFunc = segments_of_sequenceOf typeName "arr" childMinCount childMaxCount o.isFixedSize isChildPrimitive childFixedSize childMinSize childMaxSize
        let segmentsEqLemma = segments_eq_lemma_sequenceOf typeName "arr" childMinCount childMaxCount o.isFixedSize isChildPrimitive childFixedSize childMinSize childMaxSize
        ["# SequenceOf AUX"; classPredicateFunc; segmentsValidFunc; segmentsCountFunc; segmentsOfFunc; segmentsEqLemma], None

    | _, _ -> ["# SequenceOf AUX (unused)"], None
    
    

//#region IsValid Auxiliary

let generateChildValidPure (lg: ILangGeneric) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let enc = UPER // Dummy to use generateChildHelper
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> is_constraint_valid_pure_child_sequenceof childName childTypeName bIsPrimitive
        | Choice _ -> is_constraint_valid_pure_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> is_constraint_valid_pure_child_optional childName childTypeName bIsPrimitive
            | None -> is_constraint_valid_pure_child_mandatory childName childTypeName bIsPrimitive
    generateSequenceChildHelper lg enc moduleName child func

let generateSequenceIsValidAuxiliaries (lg: ILangGeneric) (r: Asn1AcnAst.AstRoot) (t: Asn1AcnAst.Asn1Type) (sq: Sequence) (typeName: string): string list =
    let asn1Children =
        sq.children |> List.choose (function
            | Asn1Child ch -> Some ch
            | _ -> None)
    
    let childValidPure =
        asn1Children |> List.map (generateChildValidPure lg t.moduleName)

    let validPureFunction = is_constraint_valid_pure_sequence typeName childValidPure
    ["# SEQUENCE Valid"; validPureFunction]

let generateByteArrayIsValidAuxiliaries (lg: ILangGeneric) (r: Asn1AcnAst.AstRoot) (t: Asn1AcnAst.Asn1Type) (expr: option<string>) (typeName: string): string list =
    let lengthExpr = 
        match t.Kind with
        | OctetString os -> if os.isFixedSize then os.maxSize.ToString() else "self.nCount"
        | _ -> "0"
    let validPureFunction = is_constraint_valid_pure_octetString typeName "arr" lengthExpr expr
    ["# ByteArray Valid"; validPureFunction]

let generateIsValidAuxiliaries (r: Asn1AcnAst.AstRoot) (t: Asn1AcnAst.Asn1Type) (typeDefinition: TypeDefinitionOrReference) (funcName: string option) (pureBody: string option) (lg: ILangGeneric): string list =
    let isPrimitive = isPrimitiveType t
    let typeName = t.FT_TypeDefinition[Python].asn1Name

    match isPrimitive, t.Kind, pureBody with
    | false, Sequence s, _-> generateSequenceIsValidAuxiliaries lg r t s typeName
    | false, OctetString _, expr -> generateByteArrayIsValidAuxiliaries lg r t expr typeName
    | false, _, Some body -> ["# NonPrimititive Valid AUX"; is_constraint_valid_pure_expr typeName body]
    | true, _, Some body -> ["# PRIMITIVE Valid AUX"; is_constraint_valid_pure_expr typeName body]
    | _ -> ["# ALWAYS TRUE Valid"; is_constraint_valid_pure_true typeName]

//#endregion
//#endregion

let generateSequenceProof(r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (sq: Asn1AcnAst.Sequence) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
    
    match codec with
    | Encode ->
        // TODO, find better solution for repeated Fold / Unfold 
        [
            "Fold(Acc(self.class_predicate(), 1/20))";
            $"Assert(codec.segments == Old(codec.segments) + {typeName}.segments_of(self))";
            "Unfold(Acc(self.class_predicate(), 1/20))"
        ]
    | Decode -> []