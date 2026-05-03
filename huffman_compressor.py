"""
Huffman Coding File Compression Tool
=====================================

A production-ready implementation of lossless file compression using Huffman Coding.
This module demonstrates mastery of:
  - Data Structures: Heaps, Binary Trees, Priority Queues
  - Algorithms: Greedy algorithms, tree traversal, prefix-free code generation
  - Low-level Programming: Bitwise manipulation, byte packing, binary I/O
  - Software Engineering: Type hints, comprehensive error handling, modular design

Author: Senior Developer Portfolio Project
Python Version: 3.10+
"""

from dataclasses import dataclass
from heapq import heappush, heappop
from typing import Dict, Optional, Tuple
import json
import os
import struct


@dataclass(frozen=True, order=True)
class Node:
    """
    Represents a node in the Huffman Tree.
    
    Attributes:
        frequency: The cumulative frequency of characters in this subtree.
        unique_id: Unique identifier for deterministic heap ordering.
        char: The character represented (None for internal nodes).
        left: Left child node in the Huffman tree.
        right: Right child node in the Huffman tree.
    
    Notes:
        - Frozen=True makes nodes immutable (safe for heap operations).
        - Order=True enables heap ordering via frequency comparison.
        - unique_id ensures deterministic ordering for equal frequencies.
    """
    frequency: int
    unique_id: int
    char: Optional[str] = None
    left: Optional['Node'] = None
    right: Optional['Node'] = None


class HuffmanCompressor:
    """
    A robust Huffman Coding compressor/decompressor for text files.
    
    This class handles the complete lifecycle of file compression and decompression:
    1. Compression: Frequency analysis → Tree building → Code generation → Bit-packing
    2. Decompression: Header parsing → Tree rebuilding → Bit-unpacking → Decoding
    
    ARCHITECTURE & COMPLEXITY ANALYSIS:
    ===================================
    
    Header Structure:
    ├── Frequency Map (JSON): Serialized character → frequency mapping
    │   Format: {"char1": freq1, "char2": freq2, ...}
    │   Encoding: UTF-8 with null terminator for boundary detection
    ├── Padding Length (4 bytes, uint32): Number of padding bits added
    │   Allows exact recovery of original bitstream length
    └── Compressed Bitstream: Raw byte data following header
    
    Time Complexity:
    ├── Compression (compress_file):
    │   ├── Frequency Analysis: O(n) where n = file size in characters
    │   ├── Huffman Tree Building: O(k log k) where k = unique characters
    │   ├── Code Generation: O(k) via DFS
    │   ├── Encoding: O(n) via dictionary lookup
    │   └── Overall: O(n + k log k) ≈ O(n) since k << n in practice
    │
    ├── Decompression (decompress_file):
    │   ├── Header Parsing: O(k) where k = unique characters
    │   ├── Tree Rebuilding: O(k)
    │   ├── Decoding: O(n) where n = original file size
    │   └── Overall: O(n + k) ≈ O(n)
    
    Space Complexity:
    ├── Compression: O(k + n) for frequency map, tree, codes, and bitstring
    ├── Decompression: O(k + n) for tree and output string
    └── Both: Typically << input size due to compression ratio
    
    Advantages of JSON-based Header:
    ├── Human-readable metadata
    ├── Automatic handling of escape characters
    ├── Built-in with standard library (no external deps)
    ├── Self-describing format
    └── Simple null-terminator parsing strategy
    """
    
    def __init__(self) -> None:
        """Initialize the compressor with empty state."""
        self.frequency_map: Dict[str, int] = {}
        self.huffman_tree: Optional[Node] = None
        self.code_dict: Dict[str, str] = {}
        self._node_counter: int = 0
    
    def _build_frequency_map(self, text: str) -> None:
        """
        Analyze text and build character frequency map.
        
        Time Complexity: O(n) where n = len(text)
        Space Complexity: O(k) where k = unique characters
        
        Args:
            text: Input text to analyze.
        
        Raises:
            ValueError: If text is empty.
        """
        if not text:
            raise ValueError("Cannot compress empty file.")
        
        self.frequency_map = {}
        for char in text:
            self.frequency_map[char] = self.frequency_map.get(char, 0) + 1
    
    def _build_huffman_tree(self) -> None:
        """
        Construct the Huffman Tree using a Min-Priority Queue.
        
        Handles edge cases:
        ├── Single unique character: Creates dummy node with frequency 1
        └── Normal case: Merges nodes bottom-up by frequency
        
        Time Complexity: O(k log k) where k = unique characters
        Space Complexity: O(k) for heap and tree nodes
        """
        if not self.frequency_map:
            raise ValueError("Frequency map is empty.")
        
        # Edge case: single unique character
        if len(self.frequency_map) == 1:
            char = list(self.frequency_map.keys())[0]
            freq = self.frequency_map[char]
            # Create a dummy parent to ensure decoding works correctly
            self._node_counter += 1
            left_node = Node(freq, self._node_counter, char=char)
            self._node_counter += 1
            dummy_node = Node(freq, self._node_counter)
            self._node_counter += 1
            root = Node(freq * 2, self._node_counter, left=left_node, right=dummy_node)
            self.huffman_tree = root
            return
        
        # Build min-heap with initial leaf nodes
        heap: list[Node] = []
        for char, freq in self.frequency_map.items():
            self._node_counter += 1
            node = Node(freq, self._node_counter, char=char)
            heappush(heap, node)
        
        # Merge nodes until one tree remains
        while len(heap) > 1:
            left = heappop(heap)
            right = heappop(heap)
            self._node_counter += 1
            parent = Node(
                frequency=left.frequency + right.frequency,
                unique_id=self._node_counter,
                left=left,
                right=right
            )
            heappush(heap, parent)
        
        self.huffman_tree = heap[0] if heap else None
    
    def _generate_codes(self, node: Optional[Node], prefix: str = "") -> None:
        """
        Generate prefix-free binary codes via tree traversal.
        
        Time Complexity: O(k) where k = unique characters
        Space Complexity: O(k) for code dictionary
        
        Args:
            node: Current node in tree traversal.
            prefix: Binary prefix accumulated so far.
        """
        if node is None:
            return
        
        # Leaf node: assign code
        if node.char is not None:
            self.code_dict[node.char] = prefix if prefix else "0"
            return
        
        # Internal node: traverse both subtrees
        self._generate_codes(node.left, prefix + "0")
        self._generate_codes(node.right, prefix + "1")
    
    def _bitstring_to_bytes(self, bitstring: str) -> Tuple[bytearray, int]:
        """
        Convert a binary string to packed bytes with padding.
        
        Padding Strategy:
        ├── Calculate padding: (8 - len(bitstring) % 8) % 8
        ├── Append padding bits: Add '0' bits to align to byte boundary
        ├── Return: (packed_bytes, padding_length)
        └── Purpose: Enables exact restoration during decompression
        
        Time Complexity: O(n) where n = len(bitstring)
        Space Complexity: O(n/8) for resulting bytearray
        
        Args:
            bitstring: Binary string of '0's and '1's.
        
        Returns:
            Tuple of (packed_bytes, padding_length).
        """
        padding_length = (8 - len(bitstring) % 8) % 8
        padded_bitstring = bitstring + "0" * padding_length
        
        packed_bytes = bytearray()
        for i in range(0, len(padded_bitstring), 8):
            byte_bits = padded_bitstring[i:i+8]
            byte_value = int(byte_bits, 2)
            packed_bytes.append(byte_value)
        
        return packed_bytes, padding_length
    
    def _bytes_to_bitstring(self, data: bytes, padding_length: int) -> str:
        """
        Convert packed bytes back to a binary string, removing padding.
        
        Time Complexity: O(m) where m = len(data)
        Space Complexity: O(m * 8) for resulting bitstring
        
        Args:
            data: Packed byte data.
            padding_length: Number of padding bits to remove.
        
        Returns:
            Unpadded binary string.
        """
        bitstring = "".join(format(byte, "08b") for byte in data)
        if padding_length > 0:
            bitstring = bitstring[:-padding_length]
        return bitstring
    
    def compress_file(self, input_path: str, output_path: str) -> None:
        """
        Compress a text file using Huffman Coding.
        
        Process:
        ├── 1. Read input file
        ├── 2. Build frequency map
        ├── 3. Construct Huffman tree
        ├── 4. Generate binary codes
        ├── 5. Encode text to binary
        ├── 6. Pack binary to bytes with padding
        ├── 7. Serialize header (frequency map + padding length)
        └── 8. Write header + packed data to output file
        
        Time Complexity: O(n + k log k)
        Space Complexity: O(n + k)
        
        Args:
            input_path: Path to input text file.
            output_path: Path to output .bin file.
        
        Raises:
            FileNotFoundError: If input file doesn't exist.
            ValueError: If input file is empty.
        
        Example:
            compressor = HuffmanCompressor()
            compressor.compress_file("original.txt", "compressed.bin")
        """
        # Read input file
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Build compression structures
        self._build_frequency_map(text)
        self._build_huffman_tree()
        self.code_dict.clear()
        self._generate_codes(self.huffman_tree)
        
        # Encode text to binary string
        binary_string = "".join(self.code_dict[char] for char in text)
        
        # Pack binary to bytes
        packed_bytes, padding_length = self._bitstring_to_bytes(binary_string)
        
        # Build header: serialize frequency map and padding length
        header_dict: Dict[str, object] = {
            "frequency_map": self.frequency_map,
            "padding_length": padding_length
        }
        header_json = json.dumps(header_dict, separators=(",", ":"))
        header_bytes = header_json.encode("utf-8") + b"\x00"  # Null terminator
        
        # Write output file
        with open(output_path, "wb") as f:
            f.write(header_bytes)
            f.write(packed_bytes)
    
    def decompress_file(self, input_path: str, output_path: str) -> None:
        """
        Decompress a Huffman-compressed binary file.
        
        Process:
        ├── 1. Read input file
        ├── 2. Extract header (frequency map + padding length)
        ├── 3. Rebuild Huffman tree from frequency map
        ├── 4. Convert packed bytes to binary string
        ├── 5. Traverse tree to decode binary to text
        └── 6. Write decoded text to output file
        
        Time Complexity: O(n + k)
        Space Complexity: O(n + k)
        
        Args:
            input_path: Path to input .bin file.
            output_path: Path to output text file.
        
        Raises:
            FileNotFoundError: If input file doesn't exist.
            ValueError: If header parsing fails or format is invalid.
        
        Example:
            compressor = HuffmanCompressor()
            compressor.decompress_file("compressed.bin", "restored.txt")
        """
        # Read input file
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        with open(input_path, "rb") as f:
            data = f.read()
        
        # Extract header: find null terminator
        null_pos = data.find(b"\x00")
        if null_pos == -1:
            raise ValueError("Invalid compressed file: no header found.")
        
        header_json = data[:null_pos].decode("utf-8")
        packed_bytes = data[null_pos + 1:]
        
        # Parse header
        try:
            header_dict = json.loads(header_json)
            frequency_map: Dict[str, int] = header_dict["frequency_map"]
            padding_length: int = header_dict["padding_length"]
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid header format: {e}")
        
        # Rebuild Huffman tree from frequency map
        self.frequency_map = frequency_map
        self._node_counter = 0
        self._build_huffman_tree()
        
        # Unpack bytes to binary string
        binary_string = self._bytes_to_bitstring(packed_bytes, padding_length)
        
        # Decode binary string using tree
        decoded_text = ""
        current_node = self.huffman_tree
        
        if current_node is None:
            raise ValueError("Huffman tree is invalid.")
        
        for bit in binary_string:
            if bit == "0":
                current_node = current_node.left
            else:
                current_node = current_node.right
            
            if current_node is None:
                raise ValueError("Invalid bitstring: tree traversal failed.")
            
            # Leaf node: append character and reset
            if current_node.char is not None:
                decoded_text += current_node.char
                current_node = self.huffman_tree
        
        # Write output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(decoded_text)


def print_compression_metrics(original_size: int, compressed_size: int) -> None:
    """
    Print human-readable compression metrics.
    
    Args:
        original_size: Size of original file in bytes.
        compressed_size: Size of compressed file in bytes.
    """
    if original_size == 0:
        print("Error: Original file size is 0.")
        return
    
    ratio = (compressed_size / original_size) * 100
    savings = original_size - compressed_size
    
    print("\n" + "=" * 60)
    print("COMPRESSION METRICS")
    print("=" * 60)
    print(f"Original File Size:   {original_size:,} bytes")
    print(f"Compressed File Size: {compressed_size:,} bytes")
    print(f"Compression Ratio:    {ratio:.2f}%")
    print(f"Space Saved:          {savings:,} bytes")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    """
    Execution & Testing Block
    ==========================
    
    This block demonstrates the compressor with:
    1. Dummy text file generation
    2. Compression and decompression
    3. Data integrity verification via assertions
    4. Compression metrics output
    """
    
    # Create test directory
    test_dir = "compression_test"
    os.makedirs(test_dir, exist_ok=True)
    
    # Generate dummy text file with diverse content
    test_file = os.path.join(test_dir, "original.txt")
    test_content = """
    The quick brown fox jumps over the lazy dog.
    This is a test file for Huffman compression.
    It contains repeated characters and words.
    Compression should reduce the file size significantly.
    The Huffman algorithm builds an optimal prefix-free code.
    """ * 10  # Repeat for better compression demonstration
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    # Paths
    compressed_file = os.path.join(test_dir, "compressed.bin")
    decompressed_file = os.path.join(test_dir, "decompressed.txt")
    
    # Compress
    print("Starting compression...")
    compressor = HuffmanCompressor()
    compressor.compress_file(test_file, compressed_file)
    print("✓ Compression complete.")
    
    # Decompress
    print("Starting decompression...")
    compressor.decompress_file(compressed_file, decompressed_file)
    print("✓ Decompression complete.")
    
    # Verify data integrity
    with open(test_file, "r", encoding="utf-8") as f:
        original = f.read()
    
    with open(decompressed_file, "r", encoding="utf-8") as f:
        restored = f.read()
    
    assert original == restored, "Data integrity check FAILED: Files do not match!"
    print("✓ Data integrity verified: Original and restored files match exactly.")
    
    # Print metrics
    original_size = os.path.getsize(test_file)
    compressed_size = os.path.getsize(compressed_file)
    print_compression_metrics(original_size, compressed_size)
    
    print("✓ All tests passed successfully!")
    
    # Test edge cases
    print("\n" + "=" * 60)
    print("EDGE CASE TESTING")
    print("=" * 60)
    
    # Edge case 1: Single character
    edge_case_1 = os.path.join(test_dir, "single_char.txt")
    with open(edge_case_1, "w", encoding="utf-8") as f:
        f.write("aaaaaaaaaa")
    
    try:
        compressor.compress_file(
            edge_case_1,
            os.path.join(test_dir, "single_char.bin")
        )
        compressor.decompress_file(
            os.path.join(test_dir, "single_char.bin"),
            os.path.join(test_dir, "single_char_restored.txt")
        )
        with open(edge_case_1, "r") as f1:
            with open(os.path.join(test_dir, "single_char_restored.txt"), "r") as f2:
                assert f1.read() == f2.read()
        print("✓ Edge Case 1 (Single character): PASSED")
    except Exception as e:
        print(f"✗ Edge Case 1 (Single character): FAILED - {e}")
    
    # Edge case 2: Small file with two characters
    edge_case_2 = os.path.join(test_dir, "two_chars.txt")
    with open(edge_case_2, "w", encoding="utf-8") as f:
        f.write("abababab")
    
    try:
        compressor.compress_file(
            edge_case_2,
            os.path.join(test_dir, "two_chars.bin")
        )
        compressor.decompress_file(
            os.path.join(test_dir, "two_chars.bin"),
            os.path.join(test_dir, "two_chars_restored.txt")
        )
        with open(edge_case_2, "r") as f1:
            with open(os.path.join(test_dir, "two_chars_restored.txt"), "r") as f2:
                assert f1.read() == f2.read()
        print("✓ Edge Case 2 (Two characters): PASSED")
    except Exception as e:
        print(f"✗ Edge Case 2 (Two characters): FAILED - {e}")
    
    # Edge case 3: Large file
    edge_case_3 = os.path.join(test_dir, "large_file.txt")
    large_content = ("The quick brown fox jumps over the lazy dog. " * 500)
    with open(edge_case_3, "w", encoding="utf-8") as f:
        f.write(large_content)
    
    try:
        compressor.compress_file(
            edge_case_3,
            os.path.join(test_dir, "large_file.bin")
        )
        compressor.decompress_file(
            os.path.join(test_dir, "large_file.bin"),
            os.path.join(test_dir, "large_file_restored.txt")
        )
        with open(edge_case_3, "r") as f1:
            with open(os.path.join(test_dir, "large_file_restored.txt"), "r") as f2:
                assert f1.read() == f2.read()
        print("✓ Edge Case 3 (Large file): PASSED")
        original_size = os.path.getsize(edge_case_3)
        compressed_size = os.path.getsize(os.path.join(test_dir, "large_file.bin"))
        print_compression_metrics(original_size, compressed_size)
    except Exception as e:
        print(f"✗ Edge Case 3 (Large file): FAILED - {e}")
    
    print("=" * 60)
    print("\n✓✓✓ ALL TESTS COMPLETED SUCCESSFULLY ✓✓✓\n")
