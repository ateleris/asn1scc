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
@Opaque
def segments_take(segments: PSeq[Segment], length: int) -> PSeq[Segment]:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(0 <= length and length <= len(segments))
    Decreases(None)
    Ensures(Result() == segments.take(length))
    Ensures(Forall(segments.take(length), lambda seg: segment_invariant(seg)))
    Ensures(Implies(length < len(segments), segments_total_length(Result()) + segments[length].length <= segments_total_length(segments)))
    
    lemma_length_monotonic = __lemma_segments_total_length_monotonic(segments, length)
    return segments.take(length)
    

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
def __lemma_segments_total_length(a: PSeq[Segment], b: PSeq[Segment]) -> bool:
    Requires(Forall(a, lambda seg: segment_invariant(seg)))
    Requires(Forall(b, lambda seg: segment_invariant(seg)))
    Requires(len(b) <= 1)
    Decreases(len(b))
    Ensures(segments_total_length(a + b) == segments_total_length(a) + segments_total_length(b))
    Ensures(Result())
    
    if len(a) == 0 or len(b) == 0:
        return True
    
    combined = a + b
    Assert(a == combined.take(len(combined) - 1))
    return segments_total_length(a + b) == segments_total_length(a) + segments_total_length(b)

@Pure
@Opaque
def __lemma_segments_total_length_monotonic(segments: PSeq[Segment], prefix: int) -> bool:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(0 <= prefix and prefix <= len(segments))
    Decreases(len(segments) - prefix)
    Ensures(segments_total_length(segments.take(prefix)) <= segments_total_length(segments))
    Ensures(Implies(prefix < len(segments), segments_total_length(segments.take(prefix)) + segments[prefix].length <= segments_total_length(segments)))
    
    if len(segments) == prefix:
        return True
    
    rec_lemma = __lemma_segments_total_length_monotonic(segments, prefix + 1)
    prev_seq = segments.take(prefix + 1)
    new_seq = segments.take(prefix)
    Assert(prev_seq.take(prefix) == new_seq) # TODO, take and drop need these additional checks
    return segments_total_length(new_seq) <= segments_total_length(segments) and rec_lemma    

@Pure
def segments_contained(byteseq: PByteSeq, segments: PSeq[Segment]) -> bool:
    """Asserts that the segments are contained in the byte sequence"""
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(segments_total_length(segments) <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(len(segments))

    if len(segments) == 0:
        return True

    last_elem = len(segments) - 1
    rec_segments = segments.take(last_elem)
    segment = segments[last_elem]

    contained = byteseq_read_bits(byteseq, segments_total_length(rec_segments), segment.length) == segment.value
    rec = segments_contained(byteseq, rec_segments)
    return contained and rec

@Pure
@Opaque
def lemma_segments_contained_monotonic(byteseq: PByteSeq, segments: PSeq[Segment], prefix: int) -> bool:
    """Asserts that segments_contained implies segments_contained for prefixes of the segments."""
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(segments_total_length(segments) <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= prefix and prefix <= len(segments))
    Requires(segments_contained(byteseq, segments))
    Decreases(len(segments) - prefix)
    Ensures(segments_contained(byteseq, segments_take(segments, prefix)))
    Ensures(Result())
        
    if prefix == len(segments):
        return True
    
    rec_lemma = lemma_segments_contained_monotonic(byteseq, segments, prefix + 1)
    rec_segments = segments_take(segments, prefix + 1)
    new_seq = segments_take(segments, prefix)
    # TODO, necessary step 
    Assert(segments_take(rec_segments, prefix) == new_seq)
    return rec_lemma and segments_contained(byteseq, new_seq)
    

@Pure
def segments_invariant(byteseq: PByteSeq, segments: PSeq[Segment]) -> bool:
    Decreases(None)
    return (Forall(segments, lambda seg: segment_invariant(seg)) and
            segments_total_length(segments) <= len(byteseq) * NO_OF_BITS_IN_BYTE and
            segments_contained(byteseq, segments))

@Pure
@Opaque
def lemma_byteseq_equal_segments_contained(b1: PByteSeq, b2: PByteSeq, equal_end: int, segments: PSeq[Segment]) -> bool:
    """Proof byteseq equality implies segments equality within that range"""
    Requires(0 <= equal_end and equal_end <= len(b1) * NO_OF_BITS_IN_BYTE and equal_end <= len(b2) * NO_OF_BITS_IN_BYTE)
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(segments_total_length(segments) <= equal_end)
    Requires(byteseq_equal_until(b1, b2, equal_end))
    Requires(segments_contained(b2, segments))
    Decreases(len(segments))
    Ensures(segments_contained(b1, segments))

    if len(segments) == 0:
        return True
    
    last_elem = len(segments) - 1
    rec_segments = segments.take(last_elem)
    segment = segments[last_elem]

    position = segments_total_length(rec_segments)

    lemma_read_bits = lemma_byteseq_equal_read_bits(b1, b2, equal_end, position, segment.length)
    b1_value = byteseq_read_bits(b1, position, segment.length)
    b2_value = byteseq_read_bits(b2, position, segment.length)
    Assert(segment.value == b2_value)

    rec = lemma_byteseq_equal_segments_contained(b1, b2, equal_end, rec_segments)
    return b1_value == b2_value and rec

@Pure
@Opaque
def lemma_segments_contained_read(byteseq: PByteSeq, segments: PSeq[Segment], index: int) -> bool:
    Requires(segments_invariant(byteseq, segments))
    Requires(0 <= index and index < len(segments))
    Decreases(len(segments))
    Ensures(byteseq_read_bits(byteseq, segments_total_length(segments_take(segments, index)), segments[index].length) == segments[index].value)
    Ensures(Result())
    
    if len(segments) - 1 == index:
        return True
    
    rec_segments = segments.take(len(segments) - 1)
    rec_lemma = lemma_segments_contained_read(byteseq, rec_segments, index)
    
    prefix_segments = segments_take(segments, index)
    Assert(prefix_segments == segments_take(rec_segments, index))
    segment = segments[index]
    Assert(segment == rec_segments[index])
    
    return rec_lemma and byteseq_read_bits(byteseq, segments_total_length(segments_take(segments, index)), segment.length) == segment.value