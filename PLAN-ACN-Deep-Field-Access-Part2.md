# Plan: ACN Deep Field Access - Part 2 (Tuple Returns & Unpacking)

## Current Status

### Completed in Part 1:
✅ Infrastructure for tracking which ACN children need to be returned by siblings
✅ Parameter passing pattern generation (`secondaryHeaderFlag=secondaryHeaderFlag`)
✅ Template signatures updated across all backends (Python, C, Scala, Ada)
✅ Analysis function `analyzeAcnChildrenToReturn()` identifies dependencies
✅ State tracking for ACN children from siblings

### Current Limitation Discovered:

The `secondaryHeaderFlag` ACN child is defined **inline** at the field usage site:
```acn
TC-CCSDS-Packet [] {
    packet-ID [] {                              -- inline ACN encoding
        packetType [],
        secondaryHeaderFlag ...,                -- ACN child belongs to THIS field
        applicationProcess-ID []
    },
    packetDataField <packet-ID.secondaryHeaderFlag> []
}
```

Not at the type definition:
```acn
TC-Packet-ID [] {                               -- type definition
    packetType [],
    --! secondaryHeaderFlag ... [],             -- commented out!
    applicationProcess-ID []
}
```

**Implication**: The ACN child `secondaryHeaderFlag` is part of the parent's (TC-CCSDS-Packet) children list, conceptually "attached" to the `packet_ID` field, not part of TC-Packet-ID's type definition.

## Problem Statement

Currently generates:
```python
# In TC_CCSDS_Packet.decode():
instance_packet_ID = TC_Packet_ID.decode(codec, check_constraints)
# secondaryHeaderFlag was decoded somewhere but is not accessible
instance_packetDataField = TC_PacketDataField.decode(
    codec, check_constraints,
    secondaryHeaderFlag=secondaryHeaderFlag  # ❌ UNDEFINED
)
```

Needs to generate:
```python
# In TC_CCSDS_Packet.decode():
instance_packet_ID, packet_ID_acn_children = TC_Packet_ID.decode(codec, check_constraints)
# packet_ID_acn_children = {'secondaryHeaderFlag': <value>}
instance_packetDataField = TC_PacketDataField.decode(
    codec, check_constraints,
    secondaryHeaderFlag=packet_ID_acn_children['secondaryHeaderFlag']  # ✅ CORRECT
)
```

## Architectural Decision Needed

Two possible approaches:

### Option A: Inline ACN Children Processing (Current Structure)
Keep inline ACN children in parent's children list, but:
1. Track which inline ACN children belong to which field
2. Decode them during the field's decode call
3. Return them as part of tuple from field decode

**Pros**: Matches ACN semantics (inline encoding)
**Cons**: Complex - needs to thread ACN children through child decode calls

### Option B: Promote Inline ACN to Type Definition
Move inline ACN children to the actual type definition during AST construction

**Pros**: Simpler - child types own their ACN children
**Cons**: Changes AST structure, may break other assumptions

**Recommended**: Option A (matches ACN specification structure)

## Implementation Steps for Part 2

### Phase 1: Inline ACN Children Tracking
1. **Modify `SequenceChildState`** to include inline ACN children for current field:
   ```fsharp
   type SequenceChildState = {
       ...
       inlineAcnChildrenForField: (string * AcnChild) list  // ACN children to decode during this field
   }
   ```

2. **Update `handleChild` for Asn1Child** to:
   - Identify inline ACN children that belong to this field (from parent's children list)
   - Pass them as additional parameters to child's encode/decode
   - Collect returned values

3. **Modify `acnParamsForTemplate`** to:
   - Include inline ACN children in parameter list
   - Generate correct references for returned ACN children

### Phase 2: Decode Template Updates

4. **Update Python `sequence_mandatory_child_decode` template**:
   ```stg
   sequence_mandatory_child_decode(..., bChildHasAcnChildrenToReturn, arrsInlineAcnChildren) ::= <<
   <if(arrsInlineAcnChildren)>
   # Decode inline ACN children first
   <arrsInlineAcnChildren:{acn|<acn.decodeStatement>}; separator="\n">
   <endif>

   <if(bChildHasAcnChildrenToReturn)>
   instance_<sChName>, <sChName>_acn_children = <sChildTypedef>.decode(
       codec, check_constraints<if(arrsAcnParams)>, <arrsAcnParams; separator=", "><endif>)
   <else>
   instance_<sChName> = <sChildTypedef>.decode(...)
   <endif>

   <if(arrsInlineAcnChildren)>
   # Add inline ACN children to return dict
   <sChName>_acn_children.update({<arrsInlineAcnChildren:{acn|'<acn.name>': <acn.varName>}; separator=", ">})
   <endif>
   >>
   ```

5. **Add ACN child decode statement generation** in DAstACN.fs

6. **Update sibling parameter resolution** to use correct dictionary:
   ```fsharp
   // Current: secondaryHeaderFlag=secondaryHeaderFlag
   // Should be: secondaryHeaderFlag=packet_ID_acn_children['secondaryHeaderFlag']
   ```

### Phase 3: Type Signature Changes

7. **Modify `createAcnFunction`** return type generation:
   ```fsharp
   let returnType =
       if acnChildrenToReturn.IsEmpty then
           typeDefinition.longTypedefName2 ...
       else
           sprintf "Tuple['%s', Dict[str, Any]]" (typeDefinition.longTypedefName2 ...)
   ```

8. **Update return statement generation** in sequence decode:
   ```python
   if acn_children_dict:
       return instance, acn_children_dict
   else:
       return instance
   ```

### Phase 4: Parameter Lookup Fix

9. **Update `acnParamsForTemplate`** (already partially done):
   ```fsharp
   match s.acnChildrenFromSiblings.TryFind (acnCh.id.ToString()) with
   | Some (siblingName, _) ->
       sprintf "%s=%s_acn_children['%s']" targetParamName siblingName acnCh.c_name
   ```

### Phase 5: Testing & Validation

10. **Generate code** with `./generate-local-tests.sh`

11. **Verify pattern** in generated TC_Packet.py:
    - TC_CCSDS_Packet.decode() decodes inline ACN child
    - Creates dict with ACN child value
    - Passes to TC_PacketDataField.decode()

12. **Test encode/decode round-trip** (if tests exist)

## Files to Modify

### F# Backend Logic
1. **BackendAst/DAstACN.fs**
   - `SequenceChildState` record
   - `handleChild` function (Asn1Child case)
   - `acnParamsForTemplate` (already partially updated)
   - Return type generation
   - Return statement generation

### Python Templates
2. **StgPython/acn_python.stg**
   - `sequence_mandatory_child_decode`
   - `sequence_optional_child_decode`
   - `sequence_default_child_decode`
   - Sequence decode function wrapper

3. **StgPython/init_python.stg** (if return type declarations needed)

### Other Backends (For Consistency)
4. **StgC/acn_c.stg** - Ignore tuple returns (C doesn't have them)
5. **StgScala/acn_scala.stg** - Use Scala tuple syntax
6. **StgAda/acn_a.stg** - Ignore or use Ada record returns

## Example: Expected Generated Code

### TC_CCSDS_Packet.decode() - Parent Sequence
```python
@classmethod
def decode(cls, codec: ACNDecoder, check_constraints: bool = True) -> 'TC_CCSDS_Packet':
    instance_packetVersionNumber = PacketTypes.PacketVersionNumberValue.decode(codec, check_constraints)

    # Decode packet_ID with inline ACN children
    instance_packetType = TC_PacketType.decode(codec, check_constraints)

    # Decode inline ACN child for packet_ID field
    secondaryHeaderFlag = PacketTypes.SecondaryHeaderFlag.decode(codec, check_constraints)

    # Decode rest of packet_ID
    instance_applicationProcess_ID = ApplicationProcess.ApplicationProcess_ID.decode(codec, check_constraints)

    # Build packet_ID instance
    instance_packet_ID = TC_Packet_ID(instance_packetType, instance_applicationProcess_ID)

    # Create ACN children dict for this field
    packet_ID_acn_children = {'secondaryHeaderFlag': secondaryHeaderFlag}

    instance_packetSequenceControl = PacketTypes.PacketSequenceControl.decode(codec, check_constraints)
    instance_packetDataLength = PacketTypes.PacketDataLength.decode(codec, check_constraints)

    # Use ACN child from packet_ID
    instance_packetDataField = TC_PacketDataField.decode(
        codec, check_constraints,
        secondaryHeaderFlag=packet_ID_acn_children['secondaryHeaderFlag']
    )

    return TC_CCSDS_Packet(...)
```

### Alternative: If ACN Children Were Part of Type Definition

If we moved inline ACN to type definition (Option B):

```python
# TC_Packet_ID.decode() would return tuple
@classmethod
def decode(cls, codec: ACNDecoder, check_constraints: bool = True) -> Tuple['TC_Packet_ID', Dict[str, Any]]:
    instance_packetType = TC_PacketType.decode(codec, check_constraints)
    secondaryHeaderFlag = PacketTypes.SecondaryHeaderFlag.decode(codec, check_constraints)
    instance_applicationProcess_ID = ApplicationProcess.ApplicationProcess_ID.decode(codec, check_constraints)

    instance = TC_Packet_ID(instance_packetType, instance_applicationProcess_ID)
    acn_children = {'secondaryHeaderFlag': secondaryHeaderFlag}

    return instance, acn_children
```

## Open Questions

1. **How to identify inline ACN children?**
   - Check if ACN child in parent's children list "belongs to" a specific Asn1 field
   - May need AST field to track parent-child relationship

2. **Should encode also return ACN children?**
   - Probably not needed - encode reads from instance
   - But may be needed for validation

3. **Performance impact of dictionary creation?**
   - Only create dict when needed
   - Could use tuple for single ACN child

4. **Type annotations for tuple returns?**
   - Need to import `Tuple` from `typing`
   - May affect generated imports section

## Success Criteria

- [ ] Generated TC_CCSDS_Packet.decode() has no undefined variables
- [ ] secondaryHeaderFlag is decoded in correct location
- [ ] packetDataField.decode() receives correct parameter value
- [ ] Code compiles without Python type errors
- [ ] Encode/decode round-trip works (if tests available)
- [ ] Pattern works for all deep field access cases in test suite

## Timeline Estimate

- Phase 1-2: Identify and decode inline ACN children: **2-3 days**
- Phase 3: Type signatures and returns: **1-2 days**
- Phase 4: Parameter lookup fixes: **1 day**
- Phase 5: Testing and iteration: **2-3 days**

**Total**: Approximately **1-1.5 weeks** of focused development

## Notes

- Current implementation (Part 1) provides all infrastructure
- Main remaining work is:
  1. Inline ACN child identification and decoding
  2. Dictionary construction
  3. Tuple return generation
- Most complex part: Threading inline ACN children through call hierarchy
