#include <stdio.h>
#include <stdint.h>
#include <string.h>


// Reference implementation:
// http://www.hackersdelight.org/hdcodetxt/crc.c.txt
// ---------------------------- reverse --------------------------------

// Reverses (reflects) bits in a 32-bit word.
unsigned reverse(unsigned x) {
   x = ((x & 0x55555555) <<  1) | ((x >>  1) & 0x55555555);
   x = ((x & 0x33333333) <<  2) | ((x >>  2) & 0x33333333);
   x = ((x & 0x0F0F0F0F) <<  4) | ((x >>  4) & 0x0F0F0F0F);
   x = (x << 24) | ((x & 0xFF00) << 8) |
       ((x >> 8) & 0xFF00) | (x >> 24);
   return x;
}
// ----------------------------- crc32a --------------------------------

/* This is the basic CRC algorithm with no optimizations. It follows the
logic circuit as closely as possible. */

unsigned int crc32a(unsigned char *message) {
   int i, j;
   unsigned int byte, crc;

   i = 0;
   crc = 0xFFFFFFFF;
   while (message[i] != 0) {
      byte = message[i];            // Get next byte.
      byte = reverse(byte);         // 32-bit reversal.
      for (j = 0; j <= 7; j++) {    // Do eight times.
         if ((int)(crc ^ byte) < 0)
              crc = (crc << 1) ^ 0x04C11DB7;
         else crc = crc << 1;
         byte = byte << 1;          // Ready next msg bit.
      }
      i = i + 1;
   }
   return reverse(~crc);
}


// Source:
// http://graphics.stanford.edu/~seander/bithacks.html#ReverseByteWith64Bits
static inline uint8_t reverse_u8(uint8_t b)
{
    return ((b * 0x80200802ULL) & 0x0884422110ULL) * 0x0101010101ULL >> 32;
}

// Description of "Standard CRC"
// http://www.repairfaq.org/filipg/LINK/F_crc_v33.html
//
// * Message data is read one byte at a time, MSB first
// * CRC is shifted left
// * XOR with non-reflected poly

// Name   : "CRC-32"
// Width  : 32
// Poly   : 04C11DB7
// Init   : FFFFFFFF
// RefIn  : True
// RefOut : True
// XorOut : FFFFFFFF
// Check  : CBF43926
uint32_t crc32(uint8_t *buf, int len)
{
    // Initial load value
    uint32_t crc = 0xffffffff;

    for (int i = 0; i < len; i += 1) {
        // Reflect input bytes (LSB first)
        uint32_t b = reverse_u8(buf[i]) << 24;

        // NOTE: Shifting the message left by 32 bits first
        // before XOR-ing with the CRC register is effectively
        // the same as padding the message with 32 zero bits
        // and following the "Standard CRC" alg above
        crc = crc ^ b;

        // When shifting left, XOR by "standard" poly
        for (int j = 0; j < 8; j += 1) {
            if (crc & 0x80000000)
                crc = (crc << 1) ^ 0x04c11db7;
            else
                crc = (crc << 1);
        }
    }

    // Reflect output bytes AND XOR by 0xffffffff (i.e. ~crc)
    return reverse(~crc);
}

uint32_t crc32_reflect(uint8_t *buf, int len) {
    // Load with reverse(initial value)
    uint32_t crc = 0xffffffff;

    for (int i = 0; i < len; i += 1) {
        crc = crc ^ buf[i];

        // XOR with reflected poly
        for (int j = 0; j < 8; j += 1) {
            if (crc & 0x1)
                crc = (crc >> 1) ^ 0xedb88320;
            else
                crc = (crc >> 1);
        }
    }

    // No need to reflect output bytes, just XOR by 0xffffffff
    return ~crc;
}

uint32_t crc32_lookup(uint8_t *buf, int len) {
    // Precompute lookup table of crc values for each byte
    static uint32_t lookup[256];
    static int lookup_init = 0;
    if (!lookup_init) {
        lookup_init = 1;
        for (uint32_t b = 0; b < 256; b += 1) {
            uint32_t crc = (b << 24);
            for (int j = 0; j < 8; j += 1) {
                if (crc & 0x80000000)
                    crc = (crc << 1) ^ 0x04c11db7;
                else
                    crc = (crc << 1);
            }
            lookup[b] = crc;
        }
    }

    // Initial load value
    uint32_t crc = 0xffffffff;

    for (int i = 0; i < len; i += 1) {
        // Reflect input bytes (LSB first)
        uint32_t b = reverse_u8(buf[i]) << 24;

        crc = (crc << 8) ^ lookup[(crc ^ b) >> 24];
    }

    // Reflect output bytes AND XOR by 0xffffffff (i.e. ~crc)
    return reverse(~crc);
}

int main()
{
    const char *str = "123456789";
    printf("%08x\n", crc32a(str));
    printf("%08x\n", crc32(str, strlen(str)));
    printf("%08x\n", crc32_reflect(str, strlen(str)));
    printf("%08x\n", crc32_lookup(str, strlen(str)));
}
