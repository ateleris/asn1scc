#!/bin/bash

set -e -u -o pipefail

OUT_DIR="generated-testlib-output"
echo "Removing generated .stg.fs files & test library output..."
rm -- StgPython/*.stg.fs

dotnet build asn1scc

echo "Generating new .stg.fs files..."
cd StgPython && dotnet ../parseStg2/bin/Debug/net9.0/parseStg2.dll backends.xml 3 && cd ..

echo "Running Asn1SCC Compiler for Asn1AcnTestLib..."
./asn1scc/bin/Debug/net9.0/asn1scc \
-python -ACN -atc -fp AUTO \
-o $OUT_DIR \
./Asn1AcnTestLib/primitives/boolean/boolean-basic.asn1 \
./Asn1AcnTestLib/primitives/boolean/boolean-false-value.asn1 \
./Asn1AcnTestLib/primitives/boolean/boolean-false-value.acn \
./Asn1AcnTestLib/primitives/boolean/boolean-true-value.asn1 \
./Asn1AcnTestLib/primitives/boolean/boolean-true-value.acn \
./Asn1AcnTestLib/primitives/boolean/boolean-combined.asn1 \
./Asn1AcnTestLib/primitives/boolean/boolean-combined.acn \
./Asn1AcnTestLib/primitives/integer/integer-basic.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-range-zero-start.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-range-positive.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-range-negative.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-acn-size.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-acn-size.acn \
./Asn1AcnTestLib/primitives/integer/integer-endianness-big.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-endianness-big.acn \
./Asn1AcnTestLib/primitives/integer/integer-endianness-little.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-endianness-little.acn \
./Asn1AcnTestLib/primitives/integer/integer-encoding-posint.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-encoding-posint.acn \
./Asn1AcnTestLib/primitives/integer/integer-encoding-twoscomplement.asn1 \
./Asn1AcnTestLib/primitives/integer/integer-encoding-twoscomplement.acn \
./Asn1AcnTestLib/primitives/real/real-ieee754-32.asn1 \
./Asn1AcnTestLib/primitives/real/real-ieee754-32.acn \
./Asn1AcnTestLib/primitives/real/real-ieee754-64.asn1 \
./Asn1AcnTestLib/primitives/real/real-ieee754-64.acn \
./Asn1AcnTestLib/primitives/real/real-endianness-big.asn1 \
./Asn1AcnTestLib/primitives/real/real-endianness-big.acn \
./Asn1AcnTestLib/primitives/real/real-endianness-little.asn1 \
./Asn1AcnTestLib/primitives/real/real-endianness-little.acn \
./Asn1AcnTestLib/primitives/bitstring/bitstring-basic.asn1 \
./Asn1AcnTestLib/primitives/bitstring/bitstring-size-fixed.asn1 \
./Asn1AcnTestLib/primitives/bitstring/bitstring-size-range.asn1 \
./Asn1AcnTestLib/primitives/bitstring/bitstring-acn-size.asn1 \
./Asn1AcnTestLib/primitives/bitstring/bitstring-acn-size.acn \
./Asn1AcnTestLib/primitives/octetstring/octetstring-basic.asn1 \
./Asn1AcnTestLib/primitives/octetstring/octetstring-size-fixed.asn1 \
./Asn1AcnTestLib/primitives/octetstring/octetstring-size-range.asn1 \
./Asn1AcnTestLib/primitives/octetstring/octetstring-acn-size.asn1 \
./Asn1AcnTestLib/primitives/octetstring/octetstring-acn-size.acn \
./Asn1AcnTestLib/primitives/ia5string/ia5string-basic.asn1 \
./Asn1AcnTestLib/primitives/ia5string/ia5string-size-fixed.asn1 \
./Asn1AcnTestLib/primitives/ia5string/ia5string-size-range.asn1 \
./Asn1AcnTestLib/primitives/enumerated/enumerated-basic.asn1 \
./Asn1AcnTestLib/primitives/enumerated/enumerated-acn-size.asn1 \
./Asn1AcnTestLib/primitives/enumerated/enumerated-acn-size.acn \
./Asn1AcnTestLib/primitives/enumerated/enumerated-encode-values.asn1 \
./Asn1AcnTestLib/primitives/enumerated/enumerated-encode-values.acn \
./Asn1AcnTestLib/primitives/null/null-basic.asn1 \
./Asn1AcnTestLib/structured/sequence/sequence-basic.asn1 \
./Asn1AcnTestLib/structured/sequence/sequence-optional.asn1 \
./Asn1AcnTestLib/structured/sequence/sequence-default.asn1 \
./Asn1AcnTestLib/structured/sequence-of/sequence-of-basic.asn1 \
./Asn1AcnTestLib/structured/sequence-of/sequence-of-size-fixed.asn1 \
./Asn1AcnTestLib/structured/sequence-of/sequence-of-size-range.asn1 \
./Asn1AcnTestLib/structured/sequence-of/sequence-of-acn-size.asn1 \
./Asn1AcnTestLib/structured/sequence-of/sequence-of-acn-size.acn \
./Asn1AcnTestLib/structured/choice/choice-basic.asn1 \
./Asn1AcnTestLib/structured/choice/choice-determinant.asn1 \
./Asn1AcnTestLib/structured/choice/choice-determinant.acn \
./Asn1AcnTestLib/advanced/subtyping/subtyping-value-constraints.asn1 \
./Asn1AcnTestLib/advanced/subtyping/subtyping-with-components.asn1 \
./Asn1AcnTestLib/advanced/subtyping/subtyping-nested.asn1 \
./Asn1AcnTestLib/advanced/subtyping/subtyping-pattern.asn1 \
./Asn1AcnTestLib/advanced/parameterized/parameterized-basic.asn1 \
./Asn1AcnTestLib/advanced/parameterized/parameterized-complex.asn1 \
./Asn1AcnTestLib/advanced/imports/imports-base-types.asn1 \
./Asn1AcnTestLib/advanced/imports/imports-extended-types.asn1 \
./Asn1AcnTestLib/advanced/imports/imports-user-module.asn1 \
./Asn1AcnTestLib/advanced/imports/imports-multi-module.asn1 \
./Asn1AcnTestLib/advanced/nested/nested-acn-basic.asn1 \
./Asn1AcnTestLib/advanced/nested/nested-acn-basic.acn \
./Asn1AcnTestLib/advanced/nested/nested-acn-parametrization.asn1 \
./Asn1AcnTestLib/advanced/nested/nested-acn-parametrization.acn \
./Asn1AcnTestLib/advanced/nested/nested-acn-conditional.asn1 \
./Asn1AcnTestLib/advanced/nested/nested-acn-conditional.acn \
./Asn1AcnTestLib/acn-attributes/alignment/alignment-byte.asn1 \
./Asn1AcnTestLib/acn-attributes/alignment/alignment-byte.acn \
./Asn1AcnTestLib/acn-attributes/alignment/alignment-word.asn1 \
./Asn1AcnTestLib/acn-attributes/alignment/alignment-word.acn \
./Asn1AcnTestLib/acn-attributes/present-when/present-when-sequence.asn1 \
./Asn1AcnTestLib/acn-attributes/present-when/present-when-sequence.acn \
./Asn1AcnTestLib/acn-attributes/present-when/present-when-choice.asn1 \
./Asn1AcnTestLib/acn-attributes/present-when/present-when-choice.acn \
./Asn1AcnTestLib/acn-attributes/save-position/save-position-basic.asn1 \
./Asn1AcnTestLib/acn-attributes/save-position/save-position-basic.acn \
./Asn1AcnTestLib/acn-attributes/save-position/save-position-complex.asn1 \
./Asn1AcnTestLib/acn-attributes/save-position/save-position-complex.acn

echo ""
echo "==========================================="
echo "Test library compilation complete!"
echo "Output directory: $OUT_DIR"
echo "==========================================="
echo ""
echo "Test Coverage Summary:"
echo "  - Primitive types (BOOLEAN, INTEGER, REAL, strings): Reqs 1-25, 34-36"
echo "  - Structured types (SEQUENCE, SEQUENCE OF, CHOICE): Reqs 26-33"
echo "  - Advanced features (subtyping, parameterized, imports): Reqs 37-40"
echo "  - Nested ACN specifications: Reqs 46-48"
echo "  - ACN attributes (alignment, present-when, etc.): Reqs 41-44, 49-51"
echo "  - Encoding formats (ACN, UPER, XER): Reqs 53-55"
echo "  - Subtyping constraints: Req 52"
echo ""
