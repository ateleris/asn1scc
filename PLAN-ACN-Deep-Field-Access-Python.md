# Plan: ACN Deep Field Access for Python Backend

## Problem Statement

When ACN specifications use parameterized encodings with deep field access (ACN 4.2 case a), where an ACN child field is used as a parameter for a sibling field's encoding/decoding, the Python backend currently does not generate correct code.

### Example from CCSDS TC-Packet

```asn1
-- ASN.1
Packet-ID ::= SEQUENCE {
    packetType PacketType,
    applicationProcess-ID ApplicationProcess-ID
}

PacketDataField ::= CHOICE {
    dataWithSecondaryHeader ...,
    dataNoSecondaryHeader ...
}

-- ACN
packet-ID [] {
    packetType [],
    secondaryHeaderFlag [],  -- ACN inserted field
    applicationProcess-ID []
}

packetDataField <packet-ID.secondaryHeaderFlag> []  -- Uses ACN child from sibling
```

### Current Behavior

The generated Python code **does not pass** the `secondaryHeaderFlag` parameter:
```python
instance_packet_ID = TC_Packet_ID.decode(codec, check_constraints)
# ... other decodes ...
instance_packetDataField = TC_PacketDataField.decode(codec, check_constraints)
# ❌ Missing: secondaryHeaderFlag parameter
```

### Why Simple Inlining Won't Work

We cannot decode ACN children in the parent scope because:
1. **OO Encapsulation**: Each class should decode its own fields from the bitstream
2. **Reusability**: `TC_Packet_ID` might be used in multiple contexts
3. **Maintainability**: Field decoding logic should stay with the field's class

## Desired Solution

### Approach: Return ACN Children from Child decode()

When a SEQUENCE has ACN children that are referenced by sibling fields, the decode method should:
1. Decode all its fields INCLUDING ACN children (in correct bitstream order)
2. Return both the instance AND any ACN child values needed by siblings

### Example Generated Code

#### Child class (TC_Packet_ID):
```python
@classmethod
def decode(cls, codec: ACNDecoder, check_constraints: bool = True) -> Tuple['TC_Packet_ID', Dict[str, Any]]:
    # Decode packetType
    instance_packetType = TC_PacketType.decode(codec, check_constraints)

    # Decode ACN child secondaryHeaderFlag (correct bitstream position)
    secondaryHeaderFlag = codec.decode_int_positive_integer_const_size(4)

    # Decode applicationProcess_ID
    instance_applicationProcess_ID = ApplicationProcess.ApplicationProcess_ID.decode(codec, check_constraints)

    instance = TC_Packet_ID(instance_packetType, instance_applicationProcess_ID)

    # Return instance and ACN children that siblings need
    acn_children = {'secondaryHeaderFlag': secondaryHeaderFlag}
    return instance, acn_children
```

#### Parent class (TC_CCSDS_Packet):
```python
@classmethod
def decode(cls, codec: ACNDecoder, check_constraints: bool = True) -> 'TC_CCSDS_Packet':
    instance_packetVersionNumber = PacketVersionNumberValue.decode(codec, check_constraints)

    # Unpack both instance and ACN children
    instance_packet_ID, packet_ID_acn_children = TC_Packet_ID.decode(codec, check_constraints)

    instance_packetSequenceControl = PacketSequenceControl.decode(codec, check_constraints)
    instance_packetDataLength = PacketDataLength.decode(codec, check_constraints)

    # Pass ACN child value to sibling that needs it
    instance_packetDataField = TC_PacketDataField.decode(
        codec,
        check_constraints,
        secondaryHeaderFlag=packet_ID_acn_children['secondaryHeaderFlag']
    )

    return TC_CCSDS_Packet(instance_packetVersionNumber, instance_packet_ID,
                           instance_packetSequenceControl, instance_packetDataLength,
                           instance_packetDataField)
```

## Implementation Plan

### Phase 1: Analysis and Data Structure Updates

#### 1.1 Analyze Dependencies in DAstACN.fs

Location: `/home/manuel/Code/Ateleris/ats-asn1scc/BackendAst/DAstACN.fs`

When processing a SEQUENCE, determine which ACN children need to be returned:
- For each ASN.1 child in the sequence
- Check if any sibling fields have `AcnDepRefTypeArgument` dependencies
- If dependency points to an `AcnChildDeterminant` in the same sequence → mark for return

**Key functions to examine:**
- `handleChild` (lines ~2034-2314): Processes each child and builds dependencies
- `acnParamsForTemplate` (lines 2052-2092): Resolves parameter sources

#### 1.2 Track ACN Children to Return

Add to the sequence processing state:
```fsharp
type SequenceChildState = {
    // ... existing fields ...
    acnChildrenToReturn: (string * AcnChild) list  // (c_name, acnChild) pairs
}
```

During child processing:
- When processing ACN child: check if any unprocessed siblings depend on it
- If yes: add to `acnChildrenToReturn`

### Phase 2: Code Generation Changes

#### 2.1 Modify Python Templates (StgPython/acn_python.stg)

**Template: `sequence_mandatory_child_decode`** (line ~1004)

Current:
```stg
instance_<sChName> = <sChildTypedef>.decode(codec, check_constraints<if(arrsAcnParams)>, <arrsAcnParams; separator=", "><endif>)
```

Enhanced:
```stg
<if(sChildHasAcnChildrenToReturn)>
instance_<sChName>, <sChName>_acn_children = <sChildTypedef>.decode(codec, check_constraints<if(arrsAcnParams)>, <arrsAcnParams; separator=", "><endif>)
<else>
instance_<sChName> = <sChildTypedef>.decode(codec, check_constraints<if(arrsAcnParams)>, <arrsAcnParams; separator=", "><endif>)
<endif>
```

**New parameter needed:**
- `sChildHasAcnChildrenToReturn`: boolean indicating if child returns ACN children

#### 2.2 Update acnParamsForTemplate Resolution

Location: `DAstACN.fs` lines 2052-2092

When building parameters for a child decode call, check if the required ACN child was returned by a sibling:

```fsharp
let acnParamsForTemplate =
  match childInfo with
  | Asn1Child child ->
      deps.acnDependencies
          |> List.filter(fun d ->
              d.asn1Type = child.Type.id &&
              match d.dependencyKind with
              | AcnDepRefTypeArgument _ -> true
              | _ -> false)
          |> List.choose(fun d ->
              match d.determinant with
              | AcnChildDeterminant acnCh ->
                  // Check if this ACN child was returned by a previous sibling
                  let siblingName = (* find which sibling contains this ACN child *)
                  Some (sprintf "%s=%s_acn_children['%s']"
                        targetParamName siblingName acnCh.c_name)
              | AcnParameterDeterminant acnPrm ->
                  (* existing logic *)
          )
  | AcnChild _ -> []
```

**Key challenge:** Need to track which sibling SEQUENCE contains each ACN child

#### 2.3 Modify Return Type Generation

**For decode methods that have ACN children to return:**

Template changes in `acn_python.stg`:
```stg
sequence_decode_return_type(sTypeDefName, bHasAcnChildrenToReturn) ::= <<
<if(bHasAcnChildrenToReturn)>
Tuple['<sTypeDefName>', Dict[str, Any]]
<else>
'<sTypeDefName>'
<endif>
>>
```

**Return statement:**
```stg
<if(bHasAcnChildrenToReturn)>
acn_children = {<arrsAcnChildrenToReturn; separator=", ">}
return instance, acn_children
<else>
return instance
<endif>
```

Where `arrsAcnChildrenToReturn` is a list like:
```
["'secondaryHeaderFlag': secondaryHeaderFlag", "'otherField': otherField"]
```

### Phase 3: Handling Nested Deep Field Access

For paths like `packet-ID.innerStruct.deepField`:
1. Inner SEQUENCE returns its ACN children to packet-ID
2. packet-ID forwards needed ACN children to parent
3. Parent passes to siblings

This requires:
- Recursive tracking through nested structures
- Path resolution to determine which intermediate containers need to forward ACN children

### Phase 4: Encode Method Consistency

**Current encode behavior:** ACN children are inlined at parent level (lines 1175-1189 in generated code)

**Decision needed:**
- Option A: Keep encode inlined (asymmetric with decode)
- Option B: Make encode symmetric - encode in child, pass value to parent, parent forwards to siblings

**Recommendation:** Option A for now (keep existing encode behavior) because:
- Less disruptive
- Encode already works correctly
- Can refactor later if symmetry is desired

### Phase 5: Testing

#### Test Cases Needed

1. **Basic deep field access** (existing TC-Packet example)
   - ACN child in sibling SEQUENCE used as parameter

2. **Multiple ACN children**
   - SEQUENCE with multiple ACN children used by different siblings

3. **Nested deep field access**
   - Path like `a.b.c` where `c` is ACN child nested in `b`

4. **Optional sequences**
   - ACN child in optional SEQUENCE used as parameter

5. **Choice determinants**
   - Similar pattern but for CHOICE types

#### Validation

- Compare generated Python with C/Scala backends
- Verify bitstream byte-by-byte compatibility
- Run existing PUSCScala test suite
- Add new test cases in `github-issues/` directory

## Files to Modify

### Primary Changes

1. **`BackendAst/DAstACN.fs`**
   - Lines 2034-2314: `handleChild` function
   - Lines 2052-2092: `acnParamsForTemplate` logic
   - Add tracking for ACN children to return
   - Modify parameter resolution

2. **`StgPython/acn_python.stg`**
   - Line ~1004: `sequence_mandatory_child_decode` template
   - Add `sequence_decode_return_type` template
   - Modify return statement generation
   - Update parameter passing for sibling ACN children

3. **`StgPython/IAcn_python.stg.fs`** (auto-generated)
   - Will be regenerated from acn_python.stg changes

### Supporting Changes

4. **`BackendAst/LanguageMacros.fs`** (potentially)
   - May need new language-specific methods for Python return type handling

5. **Test files** (validation)
   - Add test case in `github-issues/` or `PUSCScalaTest/`

## Open Questions

1. **Dict vs. Tuple for ACN children return?**
   - Dict: `{'secondaryHeaderFlag': value}` - more readable, easier to access
   - Tuple: `(value1, value2, ...)` - more efficient, type-safe with type hints
   - **Recommendation:** Dict for flexibility and readability

2. **Type hints for returned ACN children?**
   - Current: `Dict[str, Any]`
   - Better: `TypedDict` with specific fields?
   - **Recommendation:** Start with `Dict[str, Any]`, can enhance later

3. **Backward compatibility?**
   - Types without ACN dependencies will have unchanged return type
   - Types with ACN children get new return type (breaking change)
   - **Recommendation:** Accept breaking change, document in release notes

4. **Encode symmetry?**
   - Should encode also pass ACN children from child to parent?
   - **Recommendation:** Phase 2 feature, not required for MVP

## Success Criteria

- [ ] Generated Python code for TC-Packet correctly passes `secondaryHeaderFlag` parameter
- [ ] Encode/decode round-trip produces identical bitstream
- [ ] All existing tests continue to pass
- [ ] New test cases for deep field access pass
- [ ] Code generation works for nested deep field access (a.b.c)
- [ ] Documentation updated in acn_python.stg

## References

- ACN Specification Chapter 4.2: "Parameterized encodings and deep field access"
- Previous conversation summary (context from session restoration)
- TC-Packet files: `PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/ccsds/TC-Packet.{asn1,acn}`
- Existing C backend: `StgC/acn_c.stg` (for comparison)