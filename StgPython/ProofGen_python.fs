module ProofGen_python

open DAst
open FsUtils
open CommonTypes
open Language
open Asn1AcnAst
open Asn1AcnAstUtilFunctions
open AcnGenericTypes
open System.Numerics

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