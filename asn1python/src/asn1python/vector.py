"""
ASN.1 Python Runtime Library - Vector Operations

This module provides vector (array) operations for ASN.1 SEQUENCE OF and SET OF types.
"""

from typing import TypeVar, Generic, List, Optional, Iterator, Union
from .asn1_types import Asn1Error


T = TypeVar('T')


class Asn1VectorError(Asn1Error):
    """Raised when vector operations fail"""
    pass


class Asn1Vector(Generic[T]):
    """
    Generic vector class for ASN.1 SEQUENCE OF and SET OF types.

    This class provides bounds checking and ASN.1-specific operations
    for arrays of ASN.1 types.
    """

    def __init__(self,
                 initial_data: Optional[List[T]] = None):
        """
        Initialize an ASN.1 vector.

        Args:
            min_size: Minimum number of elements (None for no minimum)
            max_size: Maximum number of elements (None for no maximum)
            initial_data: Initial list of elements
        """
        self._data: List[T] = []

        if initial_data is not None:
            self.extend(initial_data)

    @property
    def size(self) -> int:
        """Get the current size of the vector"""
        return len(self._data)

    def _validate_index(self, index: int):
        """Validate that an index is within bounds"""
        if not (0 <= index < len(self._data)):
            raise Asn1VectorError(f"Index {index} out of range [0, {len(self._data)})")

    def append(self, item: T):
        """
        Append an item to the vector.

        Args:
            item: Item to append
        """
        self._data.append(item)

    def extend(self, items: List[T]):
        """
        Extend the vector with multiple items.

        Args:
            items: List of items to add
        """
        self._data.extend(items)

    def insert(self, index: int, item: T):
        """
        Insert an item at a specific index.

        Args:
            index: Index to insert at
            item: Item to insert

        Raises:
            Asn1VectorError: If the operation would violate constraints
        """
        if index < 0 or index > len(self._data):
            raise Asn1VectorError(f"Insert index {index} out of range [0, {len(self._data)}]")

        self._data.insert(index, item)

    def remove(self, item: T):
        """
        Remove the first occurrence of an item.

        Args:
            item: Item to remove

        Raises:
            Asn1VectorError: If the item is not found or removal would violate constraints
        """
        if item not in self._data:
            raise Asn1VectorError(f"Item not found in vector")

        self._data.remove(item)

    def clear(self):
        """
        Remove all items from the vector.

        Raises:
            Asn1VectorError: If clearing would violate size constraints
        """
        self._data.clear()

    def __getitem__(self, index: Union[int, slice]) -> Union[T, List[T]]:
        """Get item(s) by index or slice"""
        if isinstance(index, slice):
            return self._data[index]
        else:
            self._validate_index(index)
            return self._data[index]

    def __setitem__(self, index: Union[int, slice], value: Union[T, List[T]]):
        """Set item(s) by index or slice"""
        if isinstance(index, slice):
            if not isinstance(value, list):
                raise Asn1VectorError("Cannot assign non-list to slice")

            # Calculate new size after slice assignment
            start, stop, step = index.indices(len(self._data))
            if step == 1:
                # Simple slice replacement
                old_slice_length = stop - start
                self._data[index] = value
            else:
                # Extended slice - must have same length
                slice_length = len(range(start, stop, step))
                if len(value) != slice_length:
                    raise Asn1VectorError(f"Cannot assign {len(value)} items to slice of length {slice_length}")
                self._data[index] = value
        else:
            if isinstance(value, list):
                raise Asn1VectorError("Cannot assign list to single index")
            
            self._validate_index(index)
            self._data[index] = value

    def __len__(self) -> int:
        """Get the number of items in the vector"""
        return len(self._data)

    def __iter__(self) -> Iterator[T]:
        """Iterate over the items in the vector"""
        return iter(self._data)

    def __contains__(self, item: T) -> bool:
        """Check if an item is in the vector"""
        return item in self._data

    def __eq__(self, other) -> bool:
        """Check equality with another vector or list"""
        if isinstance(other, Asn1Vector):
            return self._data == other._data
        elif isinstance(other, list):
            return self._data == other
        return False

    def __str__(self) -> str:
        """String representation"""
        return str(self._data)

    def indexOf(self, item: T) -> int:
        """
        Find the index of an item.

        Args:
            item: Item to find

        Returns:
            Index of the item or -1 if the item is not found
        """
        try:
            return self._data.index(item)
        except ValueError:
            return -1

    def count(self, item: T) -> int:
        """
        Count occurrences of an item.

        Args:
            item: Item to count

        Returns:
            Number of occurrences
        """
        return self._data.count(item)

    def reverse(self):
        """Reverse the order of items in the vector"""
        self._data.reverse()

    def copy(self) -> 'Asn1Vector[T]':
        """
        Create a shallow copy of the vector.

        Returns:
            New vector with same constraints and data
        """
        return Asn1Vector(
            initial_data=self._data.copy()
        )

    def to_list(self) -> List[T]:
        """
        Convert to a regular Python list.

        Returns:
            List containing all items
        """
        return self._data.copy()

    def is_empty(self) -> bool:
        """
        Check if the vector is empty.

        Returns:
            True if empty, False otherwise
        """
        return len(self._data) == 0

    def slice(self, start: int, end: Optional[int] = None) -> 'Asn1Vector[T]':
        """
        Create a new vector containing a slice of this vector.

        Args:
            start: Start index
            end: End index (exclusive)

        Returns:
            New vector containing the slice
        """
        if end is None:
            end = len(self._data)

        sliced_data = self._data[start:end]

        # Create new vector with no size constraints for the slice
        return Asn1Vector(initial_data=sliced_data)