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

let generatePrecond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (codec: Codec) (lg: ILangGeneric): string list =
    let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]

    match codec with
    | Encode ->
        [
            "codec.codec_predicate() and codec.write_invariant()";
            "codec.remaining_bits >= " + string(t.maxSizeInBits enc)
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
        [
            "codec.codec_predicate() and codec.write_invariant()";
            "codec.buffer_size == Old(codec.buffer_size)";
            $"codec.segments is Old(codec.segments) + {typeName}.segments_of(self)"
        ]
    | Decode ->
        [
            "codec.codec_predicate() and codec.read_invariant()";
            "codec.segments is Old(codec.segments) and codec.buffer == Old(codec.buffer)";
            $"codec.bit_index == Old(codec.bit_index) + {usedBits}";
            $"codec.segments_read_index == Old(codec.segments_read_index) +
                {typeName}.segments_count(Old(segments_drop(codec.segments, codec.segments_read_index)))"
            $"{typeName}.segments_of(ResultT({typeName})) ==
                segments_take(segments_drop(codec.segments, Old(codec.segments_read_index)), {typeName}.segments_count(segments_drop(codec.segments, Old(codec.segments_read_index))))"
        ]
let rec isPrimitiveType (t: Asn1AcnAst.Asn1Type): bool =
    match t.Kind with
    | Integer _ | Boolean _ | Real _ | NullType _  -> true
    | _ -> false

let generateIsValidAuxiliaries (r: Asn1AcnAst.AstRoot) (t: Asn1AcnAst.Asn1Type) (typeDefinition: TypeDefinitionOrReference) (funcName: string option) (pureBody: string option) (lg: ILangGeneric): string list =
    let isPrimitive = isPrimitiveType t
    let typeName = t.FT_TypeDefinition[Python].asn1Name

    match isPrimitive, pureBody with
    | true, Some body -> [is_constraint_valid_pure_primitive typeName body]
    | false, Some body -> ["# NonPrimititive Valid AUX"]
    | _ -> [is_constraint_valid_pure_true typeName]

let generateChildHelper (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child) (func: (string -> string -> bool -> BigInteger -> string)): string =
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

let generateChildSegmentsValid (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> segments_valid_child_sequenceof childName childTypeName bIsPrimitive bitSize
        | Choice _ -> segments_valid_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> segments_valid_child_optional childName childTypeName bIsPrimitive bitSize
            | None -> segments_valid_child_mandatory childName childTypeName bIsPrimitive bitSize
    generateChildHelper lg enc moduleName child func

let generateChildSegmentCollection (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> segments_of_child_sequenceof childName childTypeName bIsPrimitive bitSize
        | Choice _ -> segments_of_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> segments_of_child_optional childName childTypeName bIsPrimitive bitSize
            | None -> segments_of_child_mandatory childName childTypeName bIsPrimitive bitSize
    generateChildHelper lg enc moduleName child func

let generateChildSegmentsCount (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> segments_count_child_sequenceof childName childTypeName bIsPrimitive bitSize
        | Choice _ -> segments_count_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> segments_count_child_optional childName childTypeName bIsPrimitive bitSize
            | None -> segments_count_child_mandatory childName childTypeName bIsPrimitive bitSize
    generateChildHelper lg enc moduleName child func

let generateChildSegmentsEqLemma (lg: ILangGeneric) (enc: Asn1Encoding) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let func (childName: string) (childTypeName: string) (bIsPrimitive: bool) (bitSize: BigInteger) =
        match child.Type.Kind with
        | SequenceOf _ -> segments_eq_lemma_child_sequenceof childName childTypeName bIsPrimitive bitSize
        | Choice _ -> segments_eq_lemma_child_choice childName childTypeName
        | _ ->
            match child.Optionality with
            | Some _ -> segments_eq_lemma_child_optional childName childTypeName bIsPrimitive bitSize
            | None -> segments_eq_lemma_child_mandatory childName childTypeName bIsPrimitive bitSize
    generateChildHelper lg enc moduleName child func 

let generateSequenceAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (sq: Asn1AcnAst.Sequence) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    match codec with
    | Decode ->
        let typeName = (lg.getSequenceTypeDefinition sq.typeDef).typeName

        let asn1Children =
            sq.children |> List.choose (function
                | Asn1Child ch -> Some ch
                | _ -> None)

        let childSegmentsValid =
            asn1Children |> List.map (generateChildSegmentsValid lg enc t.moduleName)
        let childSegments =
            asn1Children |> List.map (generateChildSegmentCollection lg enc t.moduleName)
        let childSegmentsCount =
            asn1Children |> List.map (generateChildSegmentsCount lg enc t.moduleName)
        let childSegmentsEqLemma =
            asn1Children |> List.map (generateChildSegmentsEqLemma lg enc t.moduleName)

        // Generate functions using templates
        let segmentsValidFunc = segments_valid_sequence typeName childSegmentsValid
        let segmentsOfFunc = segments_of_sequence typeName childSegments
        let segmentsCountFunc = segments_count_sequence typeName childSegmentsCount
        let segmentsEqLemma = segments_eq_lemma_sequence typeName childSegmentsEqLemma

        [segmentsValidFunc; segmentsOfFunc; segmentsCountFunc; segmentsEqLemma]
    | _ -> []

let generateChoiceAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (ch: Asn1AcnAst.Choice) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    // TODO: Implement choice auxiliaries if needed
    ["# Choice AUX"]

let generateIntegerAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (int: Asn1AcnAst.Integer) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let bitSize = t.maxSizeInBits enc
    match codec, sel.steps.IsEmpty with
    | Decode, true ->

        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let segmentsValidFunc = segments_valid_primitive typeName bitSize
        let segmentsOfFunc = segments_of_primitive typeName bitSize
        let segmentsCountFunc = segments_count_primitive typeName bitSize
        let segmentsEqLemma = segments_eq_lemma_primitive typeName bitSize

        [segmentsValidFunc; segmentsOfFunc; segmentsCountFunc; segmentsEqLemma]
    | _, _ -> ["# Integer AUX (unused)"]

let generateBooleanAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (boolean: Asn1AcnAst.Boolean) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let bitSize = t.maxSizeInBits enc
    match codec, sel.steps.IsEmpty with
    | Decode, true ->

        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let segmentsValidFunc = segments_valid_primitive typeName bitSize
        let segmentsOfFunc = segments_of_boolean typeName bitSize
        let segmentsCountFunc = segments_count_primitive typeName bitSize
        let segmentsEqLemma = segments_eq_lemma_boolean typeName bitSize

        [segmentsValidFunc; segmentsOfFunc; segmentsCountFunc; segmentsEqLemma]
    | _, _ -> ["# Boolean AUX (unused)"]

let generateNullTypeAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (nt: Asn1AcnAst.NullType) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let bitSize = t.maxSizeInBits enc
    match codec, sel.steps.IsEmpty with
    | Decode, true ->

        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let segmentsValidFunc = segments_valid_primitive typeName bitSize
        let segmentsOfFunc = segments_of_nulltype typeName bitSize
        let segmentsCountFunc = segments_count_primitive typeName bitSize
        let segmentsEqLemma = segments_eq_lemma_primitive typeName bitSize

        [segmentsValidFunc; segmentsOfFunc; segmentsCountFunc; segmentsEqLemma]
    | _, _ -> ["# NullType AUX (unused)"]

let generateEnumAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (enm: Asn1AcnAst.Enumerated) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    let bitSize = t.maxSizeInBits enc
    match codec, sel.steps.IsEmpty with
    | Decode, true ->

        let typeName = lg.getLongTypedefName t.typeDefinitionOrReference[Python]
        let segmentsValidFunc = segments_valid_primitive typeName bitSize
        let segmentsOfFunc = segments_of_primitive typeName bitSize
        let segmentsCountFunc = segments_count_primitive typeName bitSize
        let segmentsEqLemma = segments_eq_lemma_primitive typeName bitSize

        [segmentsValidFunc; segmentsOfFunc; segmentsCountFunc; segmentsEqLemma]
    | _, _ -> ["# Enum AUX (unused)"]

let generateOctetStringAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (ch: Asn1AcnAst.OctetString) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    ["# OctetString AUX"]

let generateBitStringAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (ch: Asn1AcnAst.BitString) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    ["# BitString AUX"]