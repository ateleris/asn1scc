from nagini_contracts.contracts import *
from typing import Final, Tuple

class Segment:
    
    @Predicate
    def segment_predicate(self) -> bool:
        return Acc(self._length) and Acc(self._value)
    
    def __init__(self, length: int, value: int):
        Ensures(Acc(self.segment_predicate(), 1/20))
        self._length = length
        self._value = value
        Fold(Acc(self.segment_predicate(), 1/20))
        Ensures(self.length == length)
        Ensures(self.value == value)
    
    # def __eq__(self, other: "Segment") -> bool:
    #     Requires(Rd(other.segment_predicate()))
    #     return other.length == self.length and other.value == self.value
    
    @property
    def length(self) -> int:
        Requires(Rd(self.segment_predicate()))
        Unfold(self.segment_predicate())
        return self._length
    
    @property
    def value(self) -> int:
        Requires(Rd(self.segment_predicate()))
        Unfold(self.segment_predicate())
        return self._value
    
# SegmentSeq = PSeq[Segment]