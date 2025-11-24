from nagini_contracts.adt import ADT
from nagini_contracts.contracts import *
from typing import NamedTuple
from verification import byteseq_read_bits, byteseq_equal_until, lemma_byteseq_equal_read_bits, NO_OF_BITS_IN_BYTE

class Segment_ADT(ADT):
    pass

class Segment(Segment_ADT, NamedTuple('Segment', [('length', int), ('value', int)])):
    pass

@Pure
def segment_invariant(seg: Segment) -> bool:
    Decreases(None)
    return (0 <= seg.length and seg.length <= NO_OF_BITS_IN_BYTE and 
            0 <= seg.value and seg.value < (1 << seg.length))

@Pure
def segments_total_length(segments: PSeq[Segment]) -> int:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Decreases(len(segments))
    Ensures(Result() >= 0)
    Ensures(Implies(len(segments) == 0, Result() == 0))
    Ensures(Implies(len(segments) == 1, Result() == segments[0].length))

    if len(segments) == 0:
        return 0
    
    last_elem = len(segments) - 1
    rec_segments = segments.take(last_elem)
    segment = segments[last_elem]

    return segments_total_length(rec_segments) + segment.length

@Pure
@Opaque
def __lemma_segments_total_length_induction(segments: PSeq[Segment], segment: Segment) -> bool:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(segment_invariant(segment))
    Decreases(None)
    Ensures(segments_total_length(segments) + segments_total_length(PSeq(segment)) == segments_total_length(segments + PSeq(segment)))
    Ensures(segments_total_length(segments) + segments_total_length(PSeq(segment)) == segments_total_length(PSeq(segment) + segments))
    Ensures(Result())

    combined_prefix = PSeq(segment) + segments
    combined_suffix = segments + PSeq(segment)

    segments_length = segments_total_length(segments)
    combined_suffix_length = segments_total_length(combined_suffix)
    combined_prefix_length = segments_total_length(combined_prefix)

    # Assert(combined_length == segments_total_length(combined_seq.take(len(combined_seq) - 1)) + segment.length)
    Assert(combined_prefix.drop(1) == segments)
    Assert(combined_suffix.take(len(combined_prefix) - 1) == segments)
    # Assert(segments_total_length(combined_seq.take(len(combined_seq) - 1)) == segments_length)
    # Assert(segments_total_length(PSeq(segment)) == segment.length)

    return combined_prefix_length == segments_length + segment.length and combined_suffix_length == segments_length + segment.length


# @Pure
# @Opaque
# def __lemma_segments_total_length(a: PSeq[Segment], b: PSeq[Segment]) -> bool:
#     Requires(Forall(a, lambda seg: segment_invariant(seg)))
#     Requires(Forall(b, lambda seg: segment_invariant(seg)))
#     Decreases(None)
#     Ensures(segments_total_length(a) + segments_total_length(b) == segments_total_length(a + b))
#     Ensures(Result())

#     Assert(segments_total_length(a) + segments_total_length(b.take(1)) == segments_total_length(a + b.take(1)))

#     return segments_total_length(a) + segments_total_length(b) == segments_total_length(a + b)

@Pure
def segments_contained(byteseq: PByteSeq, segments: PSeq[Segment]) -> bool:
    """Asserts that the segments are contained in the byte sequence"""
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(segments_total_length(segments) <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(len(segments))

    last_elem = len(segments) - 1
    rec_segments = segments.take(last_elem)
    segment = segments[last_elem]

    contained = byteseq_read_bits(byteseq, segments_total_length(rec_segments), segment.length) == segment.value
    rec = segments_contained(byteseq, rec_segments)
    return contained and rec

@Pure
def segments_invariant(byteseq: PByteSeq, segments: PSeq[Segment]) -> bool:
    return (Forall(segments, lambda seg: segment_invariant(seg)) and
            segments_total_length(segments) <= len(byteseq) * NO_OF_BITS_IN_BYTE and
            segments_contained(byteseq, segments))

@Pure
def __lemma_byteseq_equal_segments_contained(b1: PByteSeq, b2: PByteSeq, equal_end: int, segments: PSeq[Segment]) -> bool:
    """Proof byteseq equality implies segments equality within that range"""
    Requires(len(b1) <= len(b2))
    Requires(0 <= equal_end and equal_end <= len(b1) * NO_OF_BITS_IN_BYTE)
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(segments_total_length(segments) <= equal_end)
    Requires(byteseq_equal_until(b1, b2, equal_end))
    Requires(segments_contained(b1, segments))
    Decreases(len(segments))
    Ensures(segments_contained(b2, segments))

    if len(segments) == 0:
        return True
    
    last_elem = len(segments) - 1
    rec_segments = segments.take(last_elem)
    segment: Segment = segments[last_elem]

    position = segments_total_length(rec_segments)

    lemma_read_bits = lemma_byteseq_equal_read_bits(b1, b2, equal_end, position, segment.length)
    b1_value = byteseq_read_bits(b1, position, segment.length)
    b2_value = byteseq_read_bits(b2, position, segment.length)
    Assert(segment.value == b1_value)

    rec = __lemma_byteseq_equal_segments_contained(b1, b2, equal_end, segments.drop(1))
    return b1_value == b2_value and rec

@Pure
@Opaque
def lemma_byteseq_equal_segments_contained(b1: PByteSeq, b2: PByteSeq, equal_end: int, segments: PSeq[Segment]) -> bool:
    """Proof byteseq equality implies segments equality within that range"""
    Requires(len(b1) <= len(b2))
    Requires(0 <= equal_end and equal_end <= len(b1) * NO_OF_BITS_IN_BYTE)
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(segments_total_length(segments) <= equal_end)
    Requires(byteseq_equal_until(b1, b2, equal_end))
    Requires(segments_contained(b1, segments))
    Decreases(None)
    Ensures(segments_contained(b2, segments))

    if len(segments) == 0:
        return True
    
    empty: PSeq[Segment] = PSeq()
    return __lemma_byteseq_equal_segments_contained(b1, b2, equal_end, segments)
    
