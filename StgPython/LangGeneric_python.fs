module LangGeneric_python
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
//

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
        "", "ObjectIdentifier", asn1Name
    override this.getTimeRtlTypeName timeClass =
        let asn1Name = "TIME"
        match timeClass with
        | Asn1LocalTime                    _ -> "", "datetime", asn1Name
        | Asn1UtcTime                      _ -> "", "datetime", asn1Name
        | Asn1LocalTimeWithTimeZone        _ -> "", "datetime", asn1Name
        | Asn1Date                           -> "", "date", asn1Name
        | Asn1Date_LocalTime               _ -> "", "datetime", asn1Name
        | Asn1Date_UtcTime                 _ -> "", "datetime", asn1Name
        | Asn1Date_LocalTimeWithTimeZone   _ -> "", "datetime", asn1Name
    override this.getNullRtlTypeName = "", "None", "NULL"
    override this.getBoolRtlTypeName = "", "bool", "BOOLEAN"
    
type LangGeneric_python() =
    inherit ILangGeneric()

    override this.CreateAuxFiles var0 var1 (var2, var3) = failwith "todo"
    override this.CreateMakeFile var0 var1 = failwith "todo"
    override this.Length var0 var1 = failwith "todo"
    override this.asn1SccIntValueToString var0 unsigned = failwith "todo"
    override this.bitStringValueToByteArray(var0) = failwith "todo"
    override this.callFuncWithNoArgs() = failwith "todo"
    override this.castExpression var0 var1 = failwith "todo"
    override this.choiceIDForNone var0 var1 = failwith "todo"
    override this.createSingleLineComment(var0) = failwith "todo"
    override this.decodeEmptySeq(var0) = failwith "todo"
    override this.decode_nullType(var0) = failwith "todo"
    override this.definitionOrRef(var0) = failwith "todo"
    override this.doubleValueToString(v) =  v.ToString(FsUtils.doubleParseString, System.Globalization.NumberFormatInfo.InvariantInfo)
    override this.getAccess(var0) = "."
    override this.getAccess2(var0) = failwith "todo"
    override this.getArrayItem sel idx childTypeIsString = failwith "todo"
    override this.getAsn1ChChildBackendName(var0) = failwith "todo"
    override this.getAsn1ChChildBackendName0(var0) = failwith "todo"
    override this.getAsn1ChildBackendName(var0) = failwith "todo"
    override this.getAsn1ChildBackendName0(var0) = failwith "todo"
    override this.getChChild var0 var1 var2 = failwith "todo"
    override this.getChChildIsPresent var0 var1 var2 = failwith "todo"
    override this.getChildInfoName(var0) = failwith "todo"
    override this.getChoiceChildPresentWhenName var0 var1 = failwith "todo"
    override this.getChoiceTypeDefinition(var0) = failwith "todo"
    override this.getDirInfo var0 var1 = failwith "todo"
    override this.getEmptySequenceInitExpression(var0) = failwith "todo"
    override this.getEnumTypeDefinition(var0) = failwith "todo"
    override this.getLocalVariableDeclaration(var0) = failwith "todo"
    override this.getLongTypedefName(var0) = failwith "todo"
    override this.getNamedItemBackendName var0 var1 = failwith "todo"
    override this.getNamedItemBackendName0(var0) = failwith "todo"
    override this.getNamedItemBackendName2 var0 var1 var2 = failwith "todo"
    override this.getParamTypeSuffix var0 var1 var2 = failwith "todo"
    override this.getParamValue var0 var1 var2 = failwith "todo"
    override this.getPointer(var0) = failwith "todo"
    override this.getPointerUnchecked var0 var1 = failwith "todo"
    override this.getStar(var0) = ""
    override this.getPtrPrefix(var0) = ""
    override this.getPtrSuffix(var0) = ""
    override this.getRtlFiles var0 var1 = failwith "todo"
    override this.getSeqChild sel childName childTypeIsString childIsOptional = failwith "todo"
    override this.getSeqChildIsPresent var0 var1 = failwith "todo"
    override this.getSequenceTypeDefinition(var0) = failwith "todo"
    override this.getSizeableTypeDefinition(var0) = failwith "todo"
    override this.getStrTypeDefinition(var0) = failwith "todo"
    override this.getTopLevelDirs(var0) = failwith "todo"
    override this.getTypeDefinition(var0) = failwith "todo"
    override this.getValue(var0) = failwith "todo"
    override this.getValueAssignmentName(var0) = failwith "todo"
    override this.getValueUnchecked var0 var1 = failwith "todo"
    override this.initializeString stringSize= sprintf "bytearray(%d)" stringSize
    override this.intValueToString var0 var1 = failwith "todo"
    override this.joinSelectionUnchecked var0 var1 = failwith "todo"
    override this.presentWhenName var0 var1 = failwith "todo"
    override this.presentWhenName0 var0 var1 = failwith "todo"
    override this.setChildInfoName var0 var1 = failwith "todo"
    override this.setNamedItemBackendName0 var0 var1 = failwith "todo"
    override this.toHex n = sprintf "0x%x" n
    override this.typeDef(var0) = failwith "todo"
    override this.uper = failwith "todo"
    override this.acn = failwith "todo"
    override this.supportsStaticVerification = false
    override this.allowsSrcFilesWithNoFunctions = true
    override this.usesWrappedOptional = false
    override this.andOp = "and"
    override this.orOp = "or"
    override this.emptyStatement = ""
    override this.supportsInitExpressions = true
    override this.Keywords = failwith "todo"
    override this.init = failwith "todo"
    override this.unaryNotOperator = "not"
    override this.requiresValueAssignmentsInSrcFile = true
    override this.rtlModuleName = ""
    override this.bitStreamName = "BitStream"
    override this.decodingKind = failwith "todo"
    override this.ArrayStartIndex = 0
    override this.eqOp = "=="
    override this.atc = failwith "todo"
    override this.initMethod = failwith "todo"
    override this.neqOp = "!="
    override this.SpecNameSuffix = failwith "todo"
    override this.FalseLiteral = "False"
    override this.hasModules = true
    override this.BodyExtension = "py"
    override this.TrueLiteral = "True"
    override this.modOp = "%"
    override this.AssignOperator = "="
    override this.SpecExtension = "py"