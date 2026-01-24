from nagini_contracts.adt import ADT
from nagini_contracts.contracts import *
from typing import NamedTuple

from .verification import __lemma_byte_set_bits_value, byte_read_bits, byte_set_bits, byteseq_read_bits, byteseq_equal_until, lemma_byteseq_equal_read_bits, NO_OF_BITS_IN_BYTE, MAX_BITOP_LENGTH

class Segment_ADT(ADT):
    pass

class Segment(Segment_ADT, NamedTuple('Segment', [('length', int), ('value', int)])):
    pass

@Pure
def segment_invariant(seg: Segment) -> bool:
    Decreases(None)
    return (0 <= seg.length and seg.length <= MAX_BITOP_LENGTH and 
            0 <= seg.value and seg.value < (1 << seg.length))

@Pure
@Opaque
def segments_take(segments: PSeq[Segment], length: int) -> PSeq[Segment]:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(0 <= length and length <= len(segments))
    Decreases(None)
    Ensures(Result() is segments.take(length))
    Ensures(Forall(segments.take(length), lambda seg: segment_invariant(seg)))
    Ensures(Implies(length < len(segments), segments_total_length(Result()) + segments[length].length <= segments_total_length(segments)))
    
    lemma_length_monotonic = __lemma_segments_total_length_monotonic(segments, length)
    return segments.take(length)

@Pure
@Opaque
def segments_drop(segments: PSeq[Segment], length: int) -> PSeq[Segment]:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(0 <= length and length <= len(segments))
    Decreases(None)
    Ensures(Result() is segments.drop(length))
    Ensures(Forall(segments.drop(length), lambda seg: segment_invariant(seg)))

    return segments.drop(length)


@Pure
@Opaque
def segments_add(segments: PSeq[Segment], length: int, value: int) -> PSeq[Segment]:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(0 <= length and length <= MAX_BITOP_LENGTH)
    Requires(0 <= value and value < (1 << length))
    Decreases(None)
    Ensures(Result() is segments + PSeq(Segment(length, value)))
    Ensures(Result().take(len(segments)) is segments)
    Ensures(Forall(ResultT(PSeq[Segment]), lambda seg: segment_invariant(seg)))
    
    new_seg = segments + PSeq(Segment(length, value))
    return new_seg

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
    """Proof that reading any of the contained segments from the byte sequence returns its value"""
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

#region Conversions

@Pure
def segment_from_byte(byte: int, length: int) -> Segment:
    Requires(0 <= byte and byte < 256)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Decreases(None)
    return Segment(length, byte_read_bits(byte, 0, length))

@Pure
@Opaque
def segments_from_byteseq_full(seq: PByteSeq) -> PSeq[Segment]:
    Decreases(len(seq))
    Ensures(len(Result()) == len(seq))
    Ensures(Forall(ResultT(PSeq[Segment]), lambda seg: segment_invariant(seg)))
    Ensures(Forall(ResultT(PSeq[Segment]), lambda seg: seg.length == NO_OF_BITS_IN_BYTE))
    Ensures(Forall(int, lambda i: (Implies(0 <= i and i < len(seq), 
                                           Result()[i].value == seq[i]))))
    Ensures(segments_total_length(Result()) == len(seq) * NO_OF_BITS_IN_BYTE)
    
    length = len(seq)
    if length == 0:
        empty : PSeq[Segment] = PSeq()
        return empty
    
    prefix = segments_from_byteseq_full(seq.take(length - 1))
    last = segment_from_byte(seq[length - 1], NO_OF_BITS_IN_BYTE)
        
    full = prefix + PSeq(last)
    Assert(full.take(length - 1) == prefix)    
    return full

@Pure
@Opaque
def lemma_segments_byteseq_full(seq: PByteSeq) -> bool:
    Decreases(len(seq))
    Ensures(segments_to_byteseq_full(segments_from_byteseq_full(seq)) == seq)
    Ensures(Result())
    
    length = len(seq)
    if length == 0:
        return True
    
    prefix = segments_from_byteseq_full(seq.take(length - 1))
    full = Reveal(segments_from_byteseq_full(seq))
    Assert(full.take(length - 1) == prefix)
    
    reverse_prefix = segments_to_byteseq_full(prefix)
    prefix_eq = lemma_segments_byteseq_full(seq.take(length - 1))
        
    reverse_full = Reveal(segments_to_byteseq_full(full))
    Assert(reverse_full.take(length - 1) == reverse_prefix)
    
    return prefix_eq and reverse_full == seq

@Pure
def segments_from_byteseq(seq: PByteSeq, bit_length: PInt) -> PSeq[Segment]:
    """
    Converts bit_length bits from a sequence of bytes to segments. 
    Segments will be of 8 bits length, with potentially one partial byte at the end
    """
    Requires(0 <= bit_length and bit_length <= len(seq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(len(Result()) == (bit_length + 7) // NO_OF_BITS_IN_BYTE)
    Ensures(Forall(ResultT(PSeq[Segment]), lambda seg: segment_invariant(seg)))
    # Ensures(Result().take(bit_length // NO_OF_BITS_IN_BYTE) is 
    #         segments_from_byteseq_full(seq.take(bit_length // NO_OF_BITS_IN_BYTE)))
    Ensures(segments_total_length(Result()) == bit_length)
    
    if bit_length == 0:
        empty: PSeq[Segment] = PSeq()
        return empty

    full_bytes = bit_length // NO_OF_BITS_IN_BYTE
    full = segments_from_byteseq_full(seq.take(full_bytes))
    Assert(segments_total_length(full) == bit_length - (bit_length % NO_OF_BITS_IN_BYTE))
        
    remainder_length = bit_length % NO_OF_BITS_IN_BYTE
    if remainder_length > 0:
        
        single = segment_from_byte(seq[full_bytes], remainder_length)
        Assert(segments_total_length(full) + single.length == bit_length)
        
        full = full + PSeq(single)
        Assert(segments_total_length(full) == segments_total_length(full.take(full_bytes)) + single.length)

    return full

@Pure
@Opaque
def lemma_segments_byteseq(seq: PByteSeq, bit_length: int) -> bool:
    Requires(0 <= bit_length and bit_length <= len(seq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(byteseq_equal_until(segments_to_byteseq(segments_from_byteseq(seq, bit_length), bit_length), seq, bit_length))
    Ensures(Result())
    
    segments = segments_from_byteseq(seq, bit_length)
    reverse = segments_to_byteseq(segments, bit_length)
    
    full_count = bit_length // NO_OF_BITS_IN_BYTE
    full_bytes = segments_from_byteseq_full(seq.take(full_count))
    full_bytes_reverse = segments_to_byteseq_full(full_bytes)
    full_bytes_lemma = lemma_segments_byteseq_full(seq.take(full_count))
    Assert(full_bytes == segments.take(full_count))
    Assert(full_bytes_reverse == seq.take(full_count))
    
    Assert(Reveal(byteseq_equal_until(reverse, seq, full_count * NO_OF_BITS_IN_BYTE)))
    
    remainder_length = bit_length % NO_OF_BITS_IN_BYTE
    if remainder_length > 0:
        last = segments[full_count]
        
        lemma_byte = __lemma_byte_set_bits_value(0, last.value, 0, remainder_length)
        
        Assert(reverse[full_count] == segment_to_byte(last))
        Assert(last.value == byte_read_bits(seq[full_count], 0, remainder_length))
        Assert(byte_read_bits(reverse[full_count], 0, remainder_length) == byte_read_bits(seq[full_count], 0, remainder_length))
    
    full_eq = Reveal(byteseq_equal_until(segments_to_byteseq(segments, bit_length), seq, bit_length))
    return full_eq
    

@Pure
def segment_to_byte(segment: Segment) -> int:
    Requires(segment_invariant(segment))
    Requires(segment.length <= NO_OF_BITS_IN_BYTE)
    Decreases(None)
    return byte_set_bits(0, segment.value, 0, segment.length)

@Pure
@Opaque
def segments_to_byteseq_full(segments: PSeq[Segment]) -> PByteSeq:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(Forall(segments, lambda seg: seg.length <= NO_OF_BITS_IN_BYTE))
    Decreases(len(segments))
    Ensures(len(Result()) == len(segments))
    Ensures(Forall(int, lambda i: (Implies(0 <= i and i < len(segments), ResultT(PByteSeq)[i] == segments[i].value))))
    
    length = len(segments)
    if length == 0:
        return PByteSeq()
    
    prefix = segments_to_byteseq_full(segments.take(length - 1))
    last = segments[length - 1]
    return prefix + PByteSeq(last.value)

@Pure
def segments_to_byteseq(segments: PSeq[Segment], bit_length: int) -> PByteSeq:
    Requires(Forall(segments, lambda seg: segment_invariant(seg)))
    Requires(Forall(segments, lambda seg: seg.length <= NO_OF_BITS_IN_BYTE))
    Requires(0 <= bit_length and bit_length <= segments_total_length(segments))
    Requires(len(segments) >= (bit_length + 7) // NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(len(Result()) == (bit_length + 7) // NO_OF_BITS_IN_BYTE)
    Ensures(Implies(bit_length % NO_OF_BITS_IN_BYTE == 0, Result() == 
                    segments_to_byteseq_full(segments.take(bit_length // NO_OF_BITS_IN_BYTE))))
    
    full_bytes = bit_length // NO_OF_BITS_IN_BYTE
    full_byte_segments = segments.take(full_bytes)
    full = segments_to_byteseq_full(full_byte_segments)
    
    if bit_length % NO_OF_BITS_IN_BYTE > 0:
        single = segment_to_byte(segments[full_bytes])
        return full + PByteSeq(single)
    else:
        return full

#endregion