# UPER Python Backend - Analysis and Implementation Plan

## Current Status

**Test Status:** Currently getting import/syntax errors, unable to determine pass rate yet
**Test Command:** `pytest -n 24 generated-python-output/testlib_uper`

### Issues Identified So Far

1. ✅ **FIXED**: Missing `->` in decode function signature (line 81)
2. ✅ **FIXED**: Missing `->` in decode_pure function signature (line 98)
3. ✅ **FIXED**: Missing `@staticmethod` decorator on decode methods
4. ✅ **FIXED**: Forward reference quotes needed in type annotations
5. ✅ **FIXED**: `self.val` parameter syntax error in enum encode
6. ✅ **FIXED**: Missing error code in enum item encode
7. ✅ **FIXED**: Import statements (relative vs absolute)
8. ❌ **CURRENT BLOCKER**: Default value generation in optional field decode

---

## Problem Analysis

### Issue #8: Default Value Generation (Current Blocker)

**Error Location:** `generated-python-output/testlib_uper/asn1pylib/asn1src/SequenceDefault.py:463`

**Generated Code:**
```python
else:
    instance_counter = # init_python.stg 15
instance_counter: Optional[int] = int(0)
```

**Expected Code:**
```python
else:
    instance_counter = int(0)  # init_python.stg 15
instance_counter: Optional[int]
```

**Root Cause:**
The template is emitting the comment `# init_python.stg 15` but not the actual default value expression. This suggests:
1. Template parameter for default value is empty/missing
2. Or template is not properly substituting the value

**Investigation Path:**
1. Find template that generates optional field decode with defaults
2. Check what parameter should contain the default value
3. Trace backend code that populates this parameter
4. Fix either template or backend

---

## UPER vs ACN Differences

### Key Architectural Differences

| Aspect | ACN | UPER |
|--------|-----|------|
| **Encoding Model** | External encoding specs (ACN files) | ASN.1 constraints only |
| **Method Type** | Instance methods: `def encode(self, codec...)` | Static/instance methods mix |
| **Return Types** | Tuples with ACN children: `(value, dict)` | Simple values or Asn1SccError unions |
| **Default Values** | Rarely used (explicit ACN specs) | Common (optional fields) |
| **Discriminants** | Complex (enums, strings, integers) | Simpler (presence flags, tag values) |
| **String Handling** | Complex (external determinants) | Standard PER encoding |

### Template Organization

**ACN Templates:** `StgPython/acn_python.stg`
- Highly complex with inserted fields
- Extensive discriminant handling
- String-based choice logic

**UPER Templates:** `StgPython/uper_python.stg`
- More straightforward
- Standard PER encoding rules
- Less discriminant complexity

**Shared Templates:**
- `StgPython/header_python.stg` - Type definitions
- `StgPython/equal_python.stg` - Equality checks
- `StgPython/isvalid_python.stg` - Validation
- `StgPython/init_python.stg` - **Initialization/defaults** ⚠️

---

## Detailed Investigation Plan

### Phase 1: Understand Default Value Generation (Priority: CRITICAL)

**Goal:** Fix the missing default value in SequenceDefault.py:463

#### Step 1.1: Locate Template
```bash
grep -r "init_python.stg 15" StgPython/
grep -r "Optional field decode" StgPython/uper_python.stg
grep -n "instance_counter" generated-python-output/testlib_uper/asn1pylib/asn1src/SequenceDefault.py
```

**Expected:** Find template that generates optional field decode with `else:` clause

#### Step 1.2: Examine init_python.stg
```bash
cat StgPython/init_python.stg | head -50
```

**Look for:**
- Default value expression templates
- Parameters like `sInitValue`, `sDefaultValue`, `initExpr`
- How defaults are passed to decode templates

#### Step 1.3: Trace Backend Call
Search in F# backend for:
```bash
grep -r "init_python" BackendAst/
grep -r "defaultValue" BackendAst/DAstUPer.fs
```

**Goal:** Find where backend should be passing default value to template

#### Step 1.4: Compare with ACN
ACN likely doesn't have this issue. Check how ACN handles optional fields:
```bash
grep -A 10 "Optional field" StgPython/acn_python.stg
```

### Phase 2: Fix Default Value Generation

**Option A: Template Fix** (If value is passed but not rendered)
```python
# In uper_python.stg, find optional field decode template
else:
    <p> = <sInitValue>  # init_python.stg 15
```

**Option B: Backend Fix** (If value is not passed)
```fsharp
// In DAstUPer.fs or similar
let initExpr = getDefaultValueExpr fieldType
// Pass initExpr to template
```

**Option C: Helper Function** (If init expression needs computation)
```fsharp
// Add to backend
let getDefaultInitExpression (t: Asn1Type) : string =
    match t.Kind with
    | Integer -> "0"
    | Boolean -> "False"
    | Enumerated e -> e.items.[0].Name // First enum value
    // etc.
```

---

### Phase 3: Systematic UPER Testing (After Phase 1-2 Complete)

#### Step 3.1: Get Baseline Pass Rate
```bash
./generate-local-tests.sh
# Fix imports
sed -i '1s/^from encoder import/from .encoder import/' generated-python-output/testlib_uper/asn1pylib/asn1python/uper_encoder.py
sed -i '1s/^from decoder import/from .decoder import/' generated-python-output/testlib_uper/asn1pylib/asn1python/uper_decoder.py
# Run tests
pytest -n 24 generated-python-output/testlib_uper --tb=no -q
```

**Target:** Get actual pass/fail count

#### Step 3.2: Categorize Failures
```bash
pytest -n 24 generated-python-output/testlib_uper --tb=line -q > uper_errors.log
grep "Error\|Failed" uper_errors.log | sort | uniq -c
```

**Create categories:**
- Syntax errors (blocking)
- Import errors (blocking)
- Type errors (runtime)
- Encoding errors (semantic)
- Decoding errors (semantic)
- Validation errors (constraint checking)

#### Step 3.3: Prioritize by Impact
Order issues by number of affected tests (descending)

---

### Phase 4: Apply Learnings from ACN

Many ACN fixes will likely apply to UPER:

#### Likely Required Fixes

1. **Safe Tuple Unpacking** (if UPER uses tuples)
   - Check if UPER decode returns tuples
   - Add isinstance checks similar to ACN

2. **Variable Naming Consistency**
   - Ensure `instance_` prefix used consistently
   - Check decode variable naming

3. **Forward References**
   - Already partially fixed
   - Verify all type annotations use quotes

4. **Import Statements**
   - Already have fix script
   - Consider making permanent in templates

5. **Method Decorators**
   - Already added `@staticmethod`
   - Verify placement on all decode methods

#### Unlikely to Need

1. **ACN Children Handling** - UPER doesn't have ACN inserted fields
2. **String Discriminants** - UPER uses simpler discriminants
3. **Enum Name Mapping** - Less complex in UPER

---

### Phase 5: UPER-Specific Patterns

#### Pattern 1: Optional Fields with Presence Bits
UPER encodes presence with a single bit, then conditionally encodes value.

**Check:**
- Presence bit encoding/decoding
- Conditional value encoding/decoding
- Default value when not present

#### Pattern 2: Size Constraints
UPER has complex size constraint encoding.

**Check:**
- Length determinant encoding
- Fixed vs variable size arrays
- String length encoding

#### Pattern 3: Extension Markers
UPER supports extensible types.

**Check:**
- Extension bit handling
- Unknown extension values
- Backwards compatibility

#### Pattern 4: Choice Discriminants
UPER uses integer index for choices.

**Check:**
- Index encoding/decoding
- Out-of-range handling
- Extension choices

---

## Implementation Steps (Ordered by Priority)

### 🔴 CRITICAL - Must Fix First

#### Step 1: Fix Default Value Generation
**Time Estimate:** 2-4 hours
**Impact:** HIGH - Blocks all tests with optional fields

1. Read `StgPython/init_python.stg` completely
2. Find template for optional field initialization
3. Identify missing parameter or substitution
4. Trace backend call in `BackendAst/DAstUPer.fs`
5. Implement fix (template or backend)
6. Test with SequenceDefault.py
7. Verify all optional fields generate correctly

**Success Criteria:** `SequenceDefault.py:463` generates valid Python code

---

### 🟡 HIGH Priority - Foundation Issues

#### Step 2: Method Signature Verification
**Time Estimate:** 1 hour
**Impact:** MEDIUM - May cause type errors

1. Verify all `@staticmethod` decorators present
2. Check all return type annotations have quotes
3. Verify parameter order (codec, check_constraints, etc.)
4. Check for any remaining `<param>:` syntax errors

**Success Criteria:** All methods have valid Python signatures

#### Step 3: Import Statement Permanence
**Time Estimate:** 1 hour
**Impact:** LOW - Just quality of life

1. Find import generation in templates
2. Add relative import logic
3. Test generation
4. Remove manual sed commands from workflow

**Success Criteria:** No manual import fixes needed after generation

---

### 🟢 MEDIUM Priority - Error Handling

#### Step 4: Asn1SccError Union Type Handling
**Time Estimate:** 2-3 hours
**Impact:** MEDIUM - Affects error returns

1. Understand `Union[Type, Asn1SccError]` usage
2. Verify error case handling in decode
3. Check constraint validation returns
4. Test error propagation

**Success Criteria:** Error returns work correctly

#### Step 5: Check Constraint Flag Propagation
**Time Estimate:** 1 hour
**Impact:** LOW - Validation might be skipped

1. Verify `check_constraints` passed to nested calls
2. Check validation performed when flag is True
3. Test skip behavior when False

**Success Criteria:** Constraint checking works as expected

---

### 🔵 LOW Priority - Polish

#### Step 6: Encoder Return Value Consistency
**Time Estimate:** 1 hour
**Impact:** LOW - May return wrong status codes

1. Check what encode methods return
2. Verify 0 vs None vs error codes
3. Ensure consistency with test expectations

**Success Criteria:** Encode returns match test expectations

#### Step 7: Comment Cleanup
**Time Estimate:** 30 min
**Impact:** VERY LOW - Aesthetics

1. Remove redundant template line comments
2. Add helpful comments where unclear
3. Follow Python PEP 257 for docstrings

**Success Criteria:** Clean, readable generated code

---

## Testing Strategy

### Incremental Testing Approach

After each fix:
```bash
# Regenerate
./generate-local-tests.sh 2>&1 | tail -20

# Fix imports (until Step 3 complete)
sed -i '1s/^from encoder import/from .encoder import/' generated-python-output/testlib_uper/asn1pylib/asn1python/uper_encoder.py
sed -i '1s/^from decoder import/from .decoder import/' generated-python-output/testlib_uper/asn1pylib/asn1python/uper_decoder.py

# Run tests
pytest -n 24 generated-python-output/testlib_uper --tb=no -q 2>&1 | tail -10

# Log results
echo "After [fix name]: X passed, Y failed" >> uper_progress.log
```

### Debugging Individual Failures

```bash
# Run single test with full traceback
pytest generated-python-output/testlib_uper/asn1pylib/asn1src/test_case_001.py::test_case_UPER_000001 -v --tb=long

# Check generated code
cat generated-python-output/testlib_uper/asn1pylib/asn1src/BooleanBasic.py

# Compare with ACN equivalent
diff generated-python-output/acn/asn1pylib/asn1src/BooleanBasic.py \
     generated-python-output/testlib_uper/asn1pylib/asn1src/BooleanBasic.py
```

### Regression Prevention

```bash
# Before major change, capture current state
pytest -n 24 generated-python-output/testlib_uper --tb=no -q > uper_before.log

# After change
pytest -n 24 generated-python-output/testlib_uper --tb=no -q > uper_after.log

# Compare
diff uper_before.log uper_after.log
```

---

## Files to Investigate

### Primary Templates
1. ✅ `StgPython/uper_python.stg` - Main UPER encoding/decoding
2. ⚠️ `StgPython/init_python.stg` - **Initialization/defaults (CRITICAL)**
3. `StgPython/header_python.stg` - Type definitions
4. `StgPython/equal_python.stg` - Equality
5. `StgPython/isvalid_python.stg` - Validation

### Backend Files
1. ⚠️ `BackendAst/DAstUPer.fs` - **UPER backend logic (CRITICAL)**
2. `BackendAst/DAstProgramUnit.fs` - Module organization
3. `StgPython/LangGeneric_python.fs` - Python-specific helpers

### Interface Files (Auto-generated from .stg)
1. `StgPython/IUper_python.stg.fs` - Will regenerate from template

### Test Files
1. `generated-python-output/testlib_uper/asn1pylib/asn1src/test_case_*.py`
2. `generated-python-output/testlib_uper/asn1pylib/asn1src/SequenceDefault.py` (Current blocker)

---

## Risk Analysis

### High Risk
- **Default value generation** - Blocks many tests, complex to fix
- **Type annotation changes** - Could break many files if wrong
- **Backend changes** - Affects all generated code

### Medium Risk
- **Error handling patterns** - May need careful testing
- **Optional field logic** - Common pattern, affects many tests

### Low Risk
- **Import fixes** - Well understood, localized
- **Comment cleanup** - No functional impact
- **Decorator additions** - Already tested in ACN

---

## Success Criteria

### Phase 1 Success
- [ ] SequenceDefault.py generates valid Python
- [ ] At least one test file imports successfully
- [ ] Can get baseline test pass rate

### Phase 2 Success
- [ ] 50% of tests passing
- [ ] All syntax errors resolved
- [ ] All import errors resolved

### Phase 3 Success
- [ ] 80% of tests passing
- [ ] All common patterns working (optional fields, choices, sequences)
- [ ] Only edge cases failing

### Final Success
- [ ] 95%+ of tests passing
- [ ] All ASN.1 constructs encoded/decoded correctly
- [ ] No regressions in ACN tests
- [ ] Documentation complete

---

## Timeline Estimate

**Phase 1 (Critical Fix):** 2-4 hours
- Fix default value generation
- Get first successful test run

**Phase 2 (Foundation):** 3-5 hours
- Fix method signatures
- Fix error handling
- Get to 50% passing

**Phase 3 (Systematic Fixes):** 5-10 hours
- Fix identified patterns
- Debug edge cases
- Get to 80% passing

**Phase 4 (Polish):** 2-5 hours
- Fix remaining edge cases
- Cleanup and optimization
- Get to 95%+ passing

**Total Estimate:** 12-24 hours of focused work

---

## Next Immediate Actions

1. **Investigate init_python.stg:**
   ```bash
   cat StgPython/init_python.stg
   grep -n "15" StgPython/init_python.stg
   ```

2. **Find optional field decode template:**
   ```bash
   grep -B5 -A10 "Optional field" StgPython/uper_python.stg
   grep -B5 -A10 "else:" StgPython/uper_python.stg | grep -A10 "init_python"
   ```

3. **Examine SequenceDefault type definition:**
   ```bash
   # Look at ASN.1 source
   find . -name "*.asn1" -exec grep -l "SequenceDefault" {} \;
   # Look at generated header
   grep -B10 -A30 "class.*SequenceDefault" generated-python-output/testlib_uper/asn1pylib/asn1src/SequenceDefault.py | head -50
   ```

4. **Check backend default value handling:**
   ```bash
   grep -r "defaultValue\|initValue\|initExpr" BackendAst/DAstUPer.fs
   ```

---

## Comparison with ACN Success

**ACN Achievement:** 0% → 100% (1151/1151 tests)
**ACN Time:** Single focused session
**ACN Approach:** Systematic, pattern-based fixes

**UPER Goal:** Match ACN success
**UPER Advantage:** Can reuse many ACN solutions
**UPER Challenge:** Different encoding model, different patterns

**Key Difference:** UPER is theoretically simpler (no ACN insertions) but has its own complexity (optional fields, extensions, size constraints).

---

## Confidence Assessment

**High Confidence (>80%):**
- Can fix default value generation issue
- Can achieve >50% pass rate quickly
- Many ACN fixes will transfer

**Medium Confidence (50-80%):**
- Can achieve 95%+ pass rate
- Timeline accuracy
- No major architectural issues

**Low Confidence (<50%):**
- Achieving 100% without new edge cases
- No UPER-specific codec issues
- Backend quality for UPER vs ACN

---

## Conclusion

UPER Python backend is currently blocked on default value generation in optional field decode. Once this critical issue is fixed, we can:

1. Get baseline test pass rate
2. Apply proven patterns from ACN
3. Systematically fix UPER-specific patterns
4. Reach high pass rate (95%+)

The ACN success provides a proven methodology and many reusable solutions. UPER should be achievable with focused effort on the critical path: defaults → method signatures → error handling → edge cases.

**Recommended Start:** Immediately investigate `StgPython/init_python.stg` and trace default value generation through templates and backend.
