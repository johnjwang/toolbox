#include <stdio.h>
#include <stdint.h>

uint16_t crc16_reflect(uint8_t *buf, int len) {
    // Load with reverse(initial value)
    uint16_t crc = 0xffff;

    for (int i = 0; i < len; i += 1) {
        crc = crc ^ buf[i];

        // XOR with reflected poly
        for (int j = 0; j < 8; j += 1) {
            if (crc & 0x1)
                crc = (crc >> 1) ^ 0xa001;
            else
                crc = (crc >> 1);
        }
    }

    return crc;
}

uint16_t crc16_lookup(uint8_t *buf, int len) {
    // Precompute lookup table of crc values for each byte
    static uint16_t lookup[256];
    if (lookup[1] == 0) {
        for (int b = 0; b < 256; b += 1) {
            uint16_t crc = b;
            for (int j = 0; j < 8; j += 1) {
                if (crc & 0x1)
                    crc = (crc >> 1) ^ 0xa001;
                else
                    crc = (crc >> 1);
            }
            lookup[b] = crc;
        }
    }

    uint16_t crc = 0xffff;

    for (int i = 0; i < len; i += 1) {
        uint8_t b = buf[i] ^ crc;
        crc = (crc >> 8) ^ lookup[b];
    }

    return crc;
}


int main()
{
    uint8_t buf[1024];
    int len;
    for (len = 0; len < sizeof(buf); len += 1) {
        unsigned int tmp;

        if (scanf("%x", &tmp) == EOF)
            break;

        buf[len] = tmp;
    }
    printf("[");
    for (int i = 0; i < len; i += 1) {
        printf(" %02x", buf[i]);
    }
    printf(" ] crc : %04x\n", crc16_lookup(buf, len));
}
