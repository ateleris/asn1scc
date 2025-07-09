"""
ASN.1 Python Runtime Library - Vector Operations

This module provides vector (array) operations for ASN.1 SEQUENCE OF and SET OF types.
"""

from typing import TypeVar, Generic, List, Optional, Iterator, Union
from .types import Asn1Error, Asn1ValueError


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
                 min_size: Optional[int] = None,
                 max_size: Optional[int] = None,
                 initial_data: Optional[List[T]] = None):
        """
        Initialize an ASN.1 vector.

        Args:
            min_size: Minimum number of elements (None for no minimum)
            max_size: Maximum number of elements (None for no maximum)
            initial_data: Initial list of elements
        """
        self._min_size = min_size
        self._max_size = max_size
        self._data: List[T] = []

        if initial_data is not None:
            self.extend(initial_data)

    @property
    def min_size(self) -> Optional[int]:
        """Get the minimum size constraint"""
        return self._min_size

    @property
    def max_size(self) -> Optional[int]:
        """Get the maximum size constraint"""
        return self._max_size

    @property
    def size(self) -> int:
        """Get the current size of the vector"""
        return len(self._data)

    def _validate_size(self, new_size: int):
        """Validate that a new size meets constraints"""
        if self._min_size is not None and new_size < self._min_size:
            raise Asn1VectorError(f"Vector size {new_size} below minimum {self._min_size}")

        if self._max_size is not None and new_size > self._max_size:
            raise Asn1VectorError(f"Vector size {new_size} above maximum {self._max_size}")

    def _validate_index(self, index: int):
        """Validate that an index is within bounds"""
        if not (0 <= index < len(self._data)):
            raise Asn1VectorError(f"Index {index} out of range [0, {len(self._data)})")

    def append(self, item: T):
        """
        Append an item to the vector.

        Args:
            item: Item to append

        Raises:
            Asn1VectorError: If adding the item would violate size constraints
        """
        self._validate_size(len(self._data) + 1)
        self._data.append(item)

    def extend(self, items: List[T]):
        """
        Extend the vector with multiple items.

        Args:
            items: List of items to add

        Raises:
            Asn1VectorError: If adding the items would violate size constraints
        """
        self._validate_size(len(self._data) + len(items))
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

        self._validate_size(len(self._data) + 1)
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

        self._validate_size(len(self._data) - 1)
        self._data.remove(item)

    def pop(self, index: int = -1) -> T:
        """
        Remove and return an item at a specific index.

        Args:
            index: Index to remove from (default: last item)

        Returns:
            The removed item

        Raises:
            Asn1VectorError: If the operation would violate constraints
        """
        if not self._data:
            raise Asn1VectorError("Cannot pop from empty vector")

        if index < 0:
            index = len(self._data) + index

        self._validate_index(index)
        self._validate_size(len(self._data) - 1)

        return self._data.pop(index)

    def clear(self):
        """
        Remove all items from the vector.

        Raises:
            Asn1VectorError: If clearing would violate size constraints
        """
        self._validate_size(0)
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
                new_size = len(self._data) - old_slice_length + len(value)
                self._validate_size(new_size)
                self._data[index] = value
            else:
                # Extended slice - must have same length
                slice_length = len(range(start, stop, step))
                if len(value) != slice_length:
                    raise Asn1VectorError(f"Cannot assign {len(value)} items to slice of length {slice_length}")
                self._data[index] = value
        else:
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

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"Asn1Vector(min_size={self._min_size}, max_size={self._max_size}, data={self._data})"

    def __str__(self) -> str:
        """String representation"""
        return str(self._data)

    def index(self, item: T, start: int = 0, stop: Optional[int] = None) -> int:
        """
        Find the index of an item.

        Args:
            item: Item to find
            start: Start index for search
            stop: Stop index for search

        Returns:
            Index of the item

        Raises:
            Asn1VectorError: If the item is not found
        """
        try:
            return self._data.index(item, start, stop)
        except ValueError:
            raise Asn1VectorError(f"Item not found in vector")

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

    def sort(self, key=None, reverse=False):
        """
        Sort the items in the vector.

        Args:
            key: Function to extract comparison key
            reverse: Sort in descending order
        """
        self._data.sort(key=key, reverse=reverse)

    def copy(self) -> 'Asn1Vector[T]':
        """
        Create a shallow copy of the vector.

        Returns:
            New vector with same constraints and data
        """
        return Asn1Vector(
            min_size=self._min_size,
            max_size=self._max_size,
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

    def is_full(self) -> bool:
        """
        Check if the vector is at maximum capacity.

        Returns:
            True if at maximum size, False otherwise
        """
        return self._max_size is not None and len(self._data) >= self._max_size

    def remaining_capacity(self) -> Optional[int]:
        """
        Get the remaining capacity of the vector.

        Returns:
            Number of items that can still be added, or None if unlimited
        """
        if self._max_size is None:
            return None
        return self._max_size - len(self._data)

    def validate_constraints(self) -> bool:
        """
        Validate that the current vector satisfies all constraints.

        Returns:
            True if valid, False otherwise
        """
        try:
            self._validate_size(len(self._data))
            return True
        except Asn1VectorError:
            return False

    def resize(self, new_size: int, fill_value: Optional[T] = None):
        """
        Resize the vector to a specific size.

        Args:
            new_size: New size for the vector
            fill_value: Value to use for new elements (if growing)

        Raises:
            Asn1VectorError: If the new size violates constraints
        """
        self._validate_size(new_size)

        current_size = len(self._data)

        if new_size < current_size:
            # Shrink the vector
            self._data = self._data[:new_size]
        elif new_size > current_size:
            # Grow the vector
            if fill_value is None:
                raise Asn1VectorError("fill_value required when growing vector")

            self._data.extend([fill_value] * (new_size - current_size))

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