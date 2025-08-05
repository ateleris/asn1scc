#!/bin/bash

OUT_DIR="generated-python-output"
echo "Removing generated .stg.fs files & python-output..."
rm -- StgPython/*.stg.fs
rm -r $OUT_DIR

echo "Generating new .stg.fs files..."
cd StgPython && dotnet ../parseStg2/bin/Debug/net9.0/parseStg2.dll backends.xml 3 && cd ..

echo "Running Asn1SCC Compiler for Python..."
./asn1scc/bin/Debug/net9.0/asn1scc \
-python --acn-enc -atc --field-prefix AUTO --type-prefix T \
-o $OUT_DIR \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/common/ApplicationProcess.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/common/ApplicationProcessUser.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/common/ExecutionStep.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/common/MessageType.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/ccsds/PacketTypes.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/ccsds/TC-Packet.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/ccsds/TC-Payload.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/ErrorCodes.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-1.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-10.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-2.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-3.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-4.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-5.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-6.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-7.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-8.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/VerificationRequest.asn1 \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/common/ApplicationProcess.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/common/ApplicationProcessUser.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/common/ExecutionStep.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/common/MessageType.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/ccsds/PacketTypes.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/ccsds/TC-Packet.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/ccsds/TC-Payload.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/ErrorCodes.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-1.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-10.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-2.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-3.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-4.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-5.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-6.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-7.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/PUS-1-8.acn \
./PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/service-01/VerificationRequest.acn