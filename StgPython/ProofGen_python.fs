module ProofGen_python

open DAst
open DAstUtilFunctions
open FsUtils
open CommonTypes
open Language
open Asn1AcnAst
open Asn1AcnAstUtilFunctions
open verification_python

let generatePrecond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (codec: Codec): string list =
    match codec with
    | Encode ->
        [
            "codec.codec_predicate() and codec.write_invariant()";
            "codec.remaining_bits >= " + string(t.maxSizeInBits enc)
        ]
    | Decode ->
        [
            "codec.codec_predicate() and codec.read_invariant()";
            "codec.read_aligned(" + string(t.maxSizeInBits enc) + ")" // Not correct for dynamic sizes. TODO find solution for general approach
        ]

let generatePostcond (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (p: CodegenScope) (t: Asn1AcnAst.Asn1Type) (codec: Codec): string list =
    let usedBits = t.maxSizeInBits enc
    let typeDefName = t.FT_TypeDefinition.[Python].typeName

    match codec with
    | Encode ->
        [
            "codec.codec_predicate() and codec.write_invariant()";
            "codec.buffer_size == Old(codec.buffer_size)";
            $"codec.segments is Old(codec.segments) + PSeq(Segment({usedBits}, self.value))" // Dummy for BasicBoolean
        ]
    | Decode ->
        [
             "codec.codec_predicate() and codec.read_invariant()";
             "codec.segments is Old(codec.segments) and codec.buffer is Old(codec.buffer)";
             $"codec.bit_index == Old(codec.bit_index) + {usedBits}";
             "codec.segments_read_index == Old(codec.segments_read_index) + 1"
             "Result().success";
             $"isinstance(Result().decoded_value, {typeDefName})";
             $"Result().decoded_value == {typeDefName}(Old(codec.current_segment().value))"
        ]

// Helper function to determine if a type is primitive (has a single segment)
let rec isPrimitiveType (t: Asn1AcnAst.Asn1Type): bool =
    match t.Kind with
    | Integer _ | Boolean _ | Real _ | NullType _ | Enumerated _ -> true
    | OctetString _ | BitString _ | IA5String _ | NumericString _ -> false // These can be variable size
    | Sequence _ | SequenceOf _ | Choice _ -> false
    | ReferenceType refType -> isPrimitiveType refType.resolvedType
    | _ -> false

// Generate a child segment collection based on child type
let generateChildSegmentCollection (lg: ILangGeneric) (moduleName: string) (child: Asn1AcnAst.Asn1Child): string =
    let childName = child._python_name
    // Get the type name using the proper method
    let asn1Type: Asn1AcnAst.Asn1Type = child.Type
    let typeDefOrRef: TypeDefinitionOrReference = asn1Type.typeDefinitionOrReference.[Python]
    let childTypeDef: string = typeDefOrRef.longTypedefName2 (Some lg) lg.hasModules moduleName
    // Strip module prefix for Python if it's the current module
    let childTypeName =
        if lg.hasModules = false && childTypeDef.StartsWith((ToC moduleName) + ".") then
            childTypeDef.Substring(moduleName.Length + 1)
        else
            childTypeDef
    let bIsPrimitive = isPrimitiveType child.Type

    match child.Type.Kind with
    | SequenceOf _ -> verification_python.segments_of_child_sequenceof childName childTypeName bIsPrimitive
    | Choice _ -> verification_python.segments_of_child_choice childName childTypeName
    | _ ->
        match child.Optionality with
        | Some _ -> verification_python.segments_of_child_optional childName childTypeName bIsPrimitive
        | None -> verification_python.segments_of_child_mandatory childName childTypeName bIsPrimitive

let generateSequenceAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (sq: Asn1AcnAst.Sequence) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    // Only generate for Encode (generate once, not twice)
    match codec with
    | Encode ->
        let typeName = (lg.getSequenceTypeDefinition sq.typeDef).typeName

        // Get ASN.1 children (not ACN children)
        let asn1Children =
            sq.children |> List.choose (function
                | Asn1Child ch -> Some ch
                | _ -> None)

        // Generate child segment collection code
        let childSegments =
            asn1Children |> List.map (generateChildSegmentCollection lg t.moduleName)

        // Generate the segments_of function using the template
        let segmentsOfFunc = verification_python.segments_of_sequence typeName childSegments
        [segmentsOfFunc]
    | Decode ->
        // Don't generate for Decode - only once per type
        []

let generateIntegerAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (int: Asn1AcnAst.Integer) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    // No auxiliaries needed for primitive types
    []

let generateBooleanAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (boolean: Asn1AcnAst.Boolean) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    // No auxiliaries needed for primitive types
    []

let generateChoiceAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (ch: Asn1AcnAst.Choice) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    // TODO: Implement choice auxiliaries if needed
    []

let generateNullTypeAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (nt: Asn1AcnAst.NullType) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    // No auxiliaries needed for null type
    []

let generateEnumAuxiliaries (r: Asn1AcnAst.AstRoot) (enc: Asn1Encoding) (t: Asn1AcnAst.Asn1Type) (enm: Asn1AcnAst.Enumerated) (nestingScope: NestingScope) (sel: AccessPath) (codec: Codec) (lg: ILangGeneric): string list =
    // No auxiliaries needed for enum
    []