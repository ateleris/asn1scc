from nagini_contracts.adt import ADT
from nagini_contracts.contracts import *
from typing import NamedTuple
from verification import byteseq_read_bits, NO_OF_BITS_IN_BYTE

class Segment_ADT(ADT):
    pass

class Segment(Segment_ADT, NamedTuple('Segment', [('length', int), ('value', int)])):
    pass

@Pure
def segments_total_length(segments: PSeq[Segment]) -> int:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Decreases(len(segments))
    Ensures(Result() >= 0)
    
    if len(segments) == 0:
        return 0
    
    return segments[0].length + segments_total_length(segments.drop(1))

@Pure
def segment_invariant(seg: Segment) -> bool:
    Decreases(None)
    return (0 <= seg.length and seg.length <= NO_OF_BITS_IN_BYTE and 
            0 <= seg.value and seg.value < (1 << seg.length))

@Pure
def __segments_contained_from(byteseq: PByteSeq, position: int, segments: PSeq[Segment]) -> bool:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(0 <= position and position + segments_total_length(segments) <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(len(segments))
    
    if len(segments) == 0:
        return True
    
    segment: Segment = segments[0]
    
    Assert(segment.length <= segments_total_length(segments))
    contained = byteseq_read_bits(byteseq, position, segment.length) == segment.value
    rec = __segments_contained_from(byteseq, segment.length, segments.drop(1))
    return contained and rec

@Pure
def segments_contained(byteseq: PByteSeq, segments: PSeq[Segment]) -> bool:
    """Asserts that the segments are contained in the byte sequence"""
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(segments_total_length(segments) <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    return __segments_contained_from(byteseq, 0, segments)

@Pure
def segments_invariant(byteseq: PByteSeq, segments: PSeq[Segment]) -> bool:
    return (Forall(segments, lambda seg: segment_invariant(seg)) and
            segments_total_length(segments) <= len(byteseq) * NO_OF_BITS_IN_BYTE and
            segments_contained(byteseq, segments))