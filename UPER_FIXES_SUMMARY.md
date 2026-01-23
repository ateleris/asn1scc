# UPER Template Fixes Summary

## Overview
Fixed UPER (Unaligned Packed Encoding Rules) Python code generation templates to produce syntactically valid Python code. Used the working ACN templates as reference to ensure correct patterns.

**Status**: All generated UPER files now compile successfully with no syntax errors.

**Date**: 2026-01-09

---

## Fixes Applied

### Fix #1: Array Indexing Syntax (Lines 110, 116, 1121)

**Problem**: Templates used function call syntax `arr(<index>)` instead of bracket indexing `arr[<index>]` for array access.

**Files Modified**: `StgPython/uper_python.stg`

**Changes**:

1. **Line 110** - `InternalItem_oct_str_encode`:
```diff
-if not codec.append_byte(<p><sAcc>arr(<i>)):
+if not codec.append_byte(<p><sAcc>arr[<i>]):
```

2. **Line 116** - `InternalItem_oct_str_decode`:
```diff
-if not codec.read_byte(<p><sAcc>arr(<i>)):
+if not codec.read_byte(<p><sAcc>arr[<i>]):
```

3. **Line 1121** - `update_array_item`:
```diff
-<p>.arr(<sI>) = freshCopy(<sExpr>)
+<p>.arr[<sI>] = freshCopy(<sExpr>)
```

**Root Cause**: Template was using Scala/F#-style function call syntax instead of Python bracket indexing.

**Test**: `SequenceOfBasic.py` compiles successfully after fix.

---

### Fix #2: Enumerated Type Decode (Lines 397-416)

**Problem**: Enumerated decode used invalid match/case syntax:
- Can't match on function call result directly
- Case statements had incomplete syntax: `case 0: EnumValue` with no assignment

**Files Modified**: `StgPython/uper_python.stg`

**Changes**:

1. **Enumerated_item_decode** (Line 397-400):
```diff
-Enumerated_item_decode(p, sName, nIndex, nLastItemIndex) ::= <<
-# uper_python.stg 301
-case <nIndex>: <sName>
->>
+Enumerated_item_decode(p, sName, nIndex, nLastItemIndex) ::= <<
+# uper_python.stg 301
+if <p>_int == <nIndex>:
+    <p> = <sName>
+>>
```

2. **Enumerated_decode** (Line 408-416):
```diff
-Enumerated_decode(...) ::= <<
-# uper_python.stg 312
-# TODO: <p> = ?????
-match codec.decode_constrained_whole_number(0, <nLastItemIndex>): # uper:277
-    <arrsItem; separator="\n">
-    case _:
-        # uper_python.stg 317
-        return Asn1ConstraintValidResult(is_valid=False, error_code=<sErrCode>)
->>
+Enumerated_decode(...) ::= <<
+# uper_python.stg 312
+decoded_result = codec.decode_constrained_whole_number(0, <nLastItemIndex>)
+if not decoded_result:
+    raise Asn1Exception(f"Decoding of Constrained Whole Number failed: {decoded_result.error_message}")
+<p>_int = int(decoded_result.decoded_value)
+
+<arrsItem; separator="\n">
+>>
```

**Root Cause**: Template attempted to use Python match/case incorrectly. ACN uses if-statements for this pattern.

**Pattern**: Follow ACN template approach using sequential if statements.

**Test**: `EnumeratedBasic.py` compiles successfully and generates correct if-statement chains.

---

### Fix #3: Choice Decode Empty Variable (Lines 439-470)

**Problem**:
- `<sChoiceIndexName>` parameter was empty in generated code
- Choice decode didn't check for decode errors
- If statements had empty conditions: `if  == 0:`

**Files Modified**: `StgPython/uper_python.stg`

**Changes**:

1. **choice_decode** (Line 455-470):
```diff
-choice_decode(..., sChoiceIndexName, ...) ::= <<
-# uper_python.stg 357
-<if(bIntroSnap)>
-# @ghost val codec_0_1 = snapshot(codec)
-<endif>
-
-<sChoiceIndexName> = codec.decode_constrained_whole_number(0, <nLastItemIndex>)
-<arrsChildren: {ch|<ch>}; separator="\n">
-else:
-    # uper_python.stg 366
-    return Asn1ConstraintValidResult(is_valid=False, error_code=<sErrCode>)
-<p> = instance
->>
+choice_decode(..., sChoiceIndexName, ...) ::= <<
+# uper_python.stg 357
+<if(bIntroSnap)>
+# @ghost val codec_0_1 = snapshot(codec)
+<endif>
+
+decoded_result = codec.decode_constrained_whole_number(0, <nLastItemIndex>)
+if not decoded_result:
+    raise Asn1Exception(f"Decoding of choice index failed: {decoded_result.error_message}")
+<p>_choice_index = int(decoded_result.decoded_value)
+<arrsChildren: {ch|<ch>}; separator="\n">
+else:
+    # uper_python.stg 366
+    raise Asn1Exception(f"Decoding Exception {cls.DecodeConstants.<sErrCode>}: Invalid choice index")
+<p> = instance
+>>
```

2. **choice_child_decode** (Line 439-443):
```diff
-choice_child_decode(...) ::= <<
-# uper_python.stg 340
-if <sChoiceIndexName> == <nChildIndex>:
-    <sChildContent>
-    instance = cls(kind=<sChildID>, data=<sChildName>)
->>
+choice_child_decode(...) ::= <<
+# uper_python.stg 340
+if <p>_choice_index == <nChildIndex>:
+    <sChildContent>
+    instance = cls(kind=<sChildID>, data=<sChildName>)
+>>
```

**Root Cause**: Backend wasn't providing value for `<sChoiceIndexName>` parameter. Template made robust by generating its own variable name based on `<p>`.

**Pattern**: Template now creates `<p>_choice_index` variable directly instead of relying on backend parameter.

**Test**: `ChoiceBasic.py` compiles successfully with proper if conditions.

---

### Fix #4: Choice Encode Empty Error Code (Line 430-437)

**Problem**: Template referenced `<sErrCode>` parameter that wasn't being passed by backend, resulting in empty f-strings: `{self.EncodeConstants.}`

**Files Modified**: `StgPython/uper_python.stg`

**Changes**:

**choice_child_encode** (Line 430-437):
```diff
-choice_child_encode(p, sAcc, sChildID, nChildIndex, nIndexSizeInBits, nLastItemIndex, sChildContent, sChildName, sChildTypeDef, sChoiceTypeName, sChildInitExpr, bIsSequence, bIsEnum) ::= <<
-# uper_python.stg 333
-if <p>.kind == <sChildID>:
-    res = codec.encode_constrained_whole_number(<nChildIndex>, 0, <nLastItemIndex>)
-    if not res:
-        raise Asn1Exception(f"Encoding Exception {self.EncodeConstants.<sErrCode>}: {res.error_message}")
-    <sChildContent>
->>
+choice_child_encode(p, sAcc, sChildID, nChildIndex, nIndexSizeInBits, nLastItemIndex, sChildContent, sChildName, sChildTypeDef, sChoiceTypeName, sChildInitExpr, bIsSequence, bIsEnum) ::= <<
+# uper_python.stg 333
+if <p>.kind == <sChildID>:
+    res = codec.encode_constrained_whole_number(<nChildIndex>, 0, <nLastItemIndex>)
+    if not res:
+        raise Asn1Exception(f"Encoding Exception: {res.error_message}")
+    <sChildContent>
+>>
```

**Root Cause**: `sErrCode` not in template parameter list but was referenced in template body. Similar to Fix in enum encode.

**Pattern**: Use generic error message without error code, consistent with enum encode fix.

**Test**: `ChoiceBasic.py` compiles without f-string syntax errors.

---

## Summary Statistics

**Files Modified**: 1 (`StgPython/uper_python.stg`)
**Lines Changed**: 4 templates fixed across ~20 lines
**Syntax Errors Fixed**:
- 3 array indexing errors
- Invalid match/case syntax in enum decode
- Empty variable references in choice decode
- Empty f-string interpolations in choice encode

**Compilation Result**: ✅ All generated Python files compile successfully

---

## Key Patterns Learned

### 1. Array Access
- ❌ `arr(<index>)` - Function call syntax
- ✅ `arr[<index>]` - Python bracket indexing

### 2. Enum Decoding
- ❌ `match func():` - Can't match on function call
- ✅ Decode to variable first, then use if statements

### 3. Error Handling
- Always check decode results before using values
- Use generic error messages when error codes aren't provided by backend

### 4. Template Robustness
- Don't rely on backend parameters that may be empty
- Generate variable names from available parameters (e.g., `<p>_choice_index`)

---

## Comparison with ACN

| Aspect | ACN | UPER (Before) | UPER (After) |
|--------|-----|---------------|--------------|
| Array Access | `arr[i]` | `arr(i)` ❌ | `arr[i]` ✅ |
| Enum Decode | if statements | match/case ❌ | if statements ✅ |
| Error Checking | Always checks | Inconsistent ❌ | Always checks ✅ |
| Variable Names | Backend provided | Empty ❌ | Template generated ✅ |

---

## Testing

All test files compile successfully:
```bash
python -m compileall generated-python-output/testlib_uper/asn1pylib/asn1src/
# Result: All files compiled successfully!
```

Key files verified:
- ✅ `EnumeratedBasic.py` - Enum decode with if statements
- ✅ `ChoiceBasic.py` - Choice encode/decode with proper variables
- ✅ `SequenceOfBasic.py` - Array indexing with brackets
- ✅ `SequenceDefault.py` - Default value initialization

---

## Next Steps

1. ✅ All syntax errors resolved
2. 🔲 Run pytest to check runtime behavior
3. 🔲 Fix any remaining semantic/logic errors
4. 🔲 Bring UPER test pass rate to 100% like ACN
5. 🔲 Fix import statements (currently require sed post-processing)

---

## Build Commands

```bash
# Regenerate code
./generate-local-tests.sh python

# Verify syntax
python -m compileall generated-python-output/testlib_uper/asn1pylib/asn1src/

# Run tests (requires pytest setup)
# pytest generated-python-output/testlib_uper/
```
