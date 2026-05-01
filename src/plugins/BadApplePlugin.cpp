#include "plugins/BadApplePlugin.h"
#include <cstring>
#include <vector>

// ── Compressed Huffman data produced by ikea-huf.py ───────────────────────────
// File format:
//   [4 B]  magic "IHUF"
//   [4 B]  frame count         (uint32 big-endian)
//   [4 B]  tree bit-length     (uint32 big-endian)
//   [N B]  tree bytes          (pre-order: '0'=internal node, '1'+byte=leaf)
//   per frame:
//     [4 B]  compressed bit-length  (uint32 big-endian)
//     [N B]  compressed bytes       (MSB-first, zero-padded to byte boundary)
static const uint8_t huf_data[] = {
#include "badApple.h"
};

#define FRAME_PIXELS 256
#define HUF_MAX_NODES 511  // 2*256-1, enough for all possible byte values

// ── Flat Huffman node array (populated once in setup) ─────────────────────────
struct HufNode {
    int16_t symbol; // >= 0 for a leaf, -1 for an internal node
    int16_t left;   // child index; -1 if unused
    int16_t right;
};

static HufNode  huf_nodes[HUF_MAX_NODES];
static int      huf_node_count = 0;
static int16_t  huf_root_idx   = 0;

// ── Per-frame index (built in setup, used every loop) ─────────────────────────
static int                   huf_frame_count = 0;
static std::vector<uint32_t> frame_bit_off;  // bit offset of compressed data
static std::vector<uint32_t> frame_bit_len;  // number of valid compressed bits

// ── Bit-level reader (MSB-first per byte) ─────────────────────────────────────
struct BitReader {
    const uint8_t* data;
    uint32_t       pos; // current bit position

    uint8_t readBit() {
        uint8_t b = (data[pos >> 3] >> (7u - (pos & 7u))) & 1u;
        ++pos;
        return b;
    }

    uint8_t readByte() {
        uint8_t v = 0;
        for (int i = 0; i < 8; i++) v = (uint8_t)((v << 1) | readBit());
        return v;
    }

    // Must be called on a byte boundary
    uint32_t readU32BE() {
        uint32_t o = pos >> 3;
        uint32_t v = ((uint32_t)data[o]     << 24) |
                     ((uint32_t)data[o + 1] << 16) |
                     ((uint32_t)data[o + 2] <<  8) |
                      (uint32_t)data[o + 3];
        pos += 32;
        return v;
    }
};

// ── Tree deserialization (pre-order: bit 0 = internal, bit 1 = leaf + byte) ───
static int16_t deserializeNode(BitReader& br) {
    int16_t idx = (int16_t)(huf_node_count++);
    if (br.readBit() == 1) {
        huf_nodes[idx] = { (int16_t)br.readByte(), -1, -1 };
    } else {
        huf_nodes[idx].symbol = -1;
        huf_nodes[idx].left   = deserializeNode(br);
        huf_nodes[idx].right  = deserializeNode(br);
    }
    return idx;
}

// ── Decode FRAME_PIXELS symbols from br using the pre-built tree ──────────────
static void decodeFrame(BitReader& br, uint8_t* out) {
    if (huf_nodes[huf_root_idx].symbol >= 0) {
        // Edge case: only one unique symbol in the whole video
        memset(out, (uint8_t)huf_nodes[huf_root_idx].symbol, FRAME_PIXELS);
        return;
    }
    for (int i = 0; i < FRAME_PIXELS; i++) {
        int16_t node = huf_root_idx;
        while (huf_nodes[node].symbol < 0)
            node = br.readBit() ? huf_nodes[node].right : huf_nodes[node].left;
        out[i] = (uint8_t)huf_nodes[node].symbol;
    }
}

// ─────────────────────────────────────────────────────────────────────────────

void BadApplePlugin::setup()
{
    this->frame = 0;
    huf_frame_count = 0;
    frame_bit_off.clear();
    frame_bit_len.clear();

    if (sizeof(huf_data) < 12) return;

    if (huf_data[0] != 'I' || huf_data[1] != 'H' ||
        huf_data[2] != 'U' || huf_data[3] != 'F') return;

    BitReader br{huf_data, 32};            // start after 4-byte magic

    huf_frame_count        = (int)br.readU32BE();   // bytes 4-7
    uint32_t tree_bits     = br.readU32BE();          // bytes 8-11
    uint32_t tree_byte_cnt = (tree_bits + 7u) / 8u;

    // Deserialize tree (starts at bit 96, i.e. byte 12)
    huf_node_count = 0;
    huf_root_idx   = deserializeNode(br);

    // Seek past tree padding to first frame header
    br.pos = (12u + tree_byte_cnt) * 8u;

    frame_bit_off.reserve(huf_frame_count);
    frame_bit_len.reserve(huf_frame_count);
    for (int i = 0; i < huf_frame_count; i++) {
        uint32_t nbits = br.readU32BE();              // 4-byte frame bit-length
        frame_bit_len.push_back(nbits);
        frame_bit_off.push_back(br.pos);              // compressed data starts here
        br.pos += ((nbits + 7u) / 8u) * 8u;          // advance past padded frame bytes
    }
}

void BadApplePlugin::loop()
{
    if (huf_frame_count == 0) return;

    uint8_t pixels[FRAME_PIXELS];
    BitReader br{huf_data, frame_bit_off[this->frame]};
    decodeFrame(br, pixels);

    for (int i = 0; i < FRAME_PIXELS; i++)
        Screen.setPixelAtIndex(i, 1, pixels[i]);

    if (++this->frame >= (uint32_t)huf_frame_count)
        this->frame = 0;

    auto const frameDelay = 33; // 30 FPS
#ifdef ESP32
    vTaskDelay(pdMS_TO_TICKS(frameDelay));
#else
    delay(frameDelay);
#endif
}

const char *BadApplePlugin::getName() const
{
    return "BadApple";
}
