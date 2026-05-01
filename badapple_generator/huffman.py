import heapq
from collections import Counter
from collections import namedtuple

# Node structure
class Node(namedtuple("Node", ["char", "freq", "left", "right"])):
    def __lt__(self, other):
        return self.freq < other.freq


def build_tree(data):
    frequency = Counter(data)
    heap = [Node(char, freq, None, None) for char, freq in frequency.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = Node(None, left.freq + right.freq, left, right)
        heapq.heappush(heap, merged)

    return heap[0]


def build_codes(node, prefix="", codebook={}):
    if node is None:
        return

    if node.char is not None:
        codebook[node.char] = prefix
        return

    build_codes(node.left, prefix + "0", codebook)
    build_codes(node.right, prefix + "1", codebook)

    return codebook


def encode_data(data, codebook):
    return ''.join(codebook[byte] for byte in data)


def pad_encoded_data(encoded):
    extra_bits = 8 - len(encoded) % 8
    encoded += "0" * extra_bits
    padded_info = f"{extra_bits:08b}"
    return padded_info + encoded


def to_bytes(padded_encoded):
    return bytes(int(padded_encoded[i:i+8], 2)
                 for i in range(0, len(padded_encoded), 8))


def compress(input_path, output_path):
    # Read file as bytes
    with open(input_path, "rb") as f:
        data = f.read()

    # Build Huffman tree
    tree = build_tree(data)

    # Build codebook
    codebook = build_codes(tree)

    # Encode data
    encoded = encode_data(data, codebook)

    # Pad and convert to bytes
    padded = pad_encoded_data(encoded)
    compressed_data = to_bytes(padded)

    # Save compressed file
    with open(output_path, "wb") as f:
        f.write(compressed_data)

    return codebook