#include <ctype.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern uint64_t a64_add_flags(uint64_t a, uint64_t b, uint64_t *nzcv);

struct test_case {
    const char *name;
    uint64_t a, b, sum, nzcv;
};

/* Independent fixed expectations; NZCV occupies bits 31:28. */
static const struct test_case cases[] = {
    {"positive", 1, 2, 3, 0x00000000},
    {"zero", 0, 0, 0, 0x40000000},
    {"unsigned_carry", UINT64_MAX, 1, 0, 0x60000000},
    {"signed_positive_overflow", 0x7fffffffffffffff, 1,
     0x8000000000000000, 0x90000000},
    {"signed_negative_overflow", 0x8000000000000000, 0x8000000000000000,
     0, 0x70000000},
    {"negative_with_carry", UINT64_MAX, UINT64_MAX,
     0xfffffffffffffffe, 0xa0000000},
};

int main(int argc, char **argv)
{
    if ((argc != 2 && argc != 3) || strlen(argv[1]) != 32 ||
        (argc == 3 && strcmp(argv[2], "--inject-failure") != 0)) {
        fputs("usage: isa_add_flags NONCE_32_HEX [--inject-failure]\n", stderr);
        return 2;
    }
    for (size_t i = 0; i < 32; ++i) {
        if (!isxdigit((unsigned char)argv[1][i]))
            return 2;
    }

    const int injected = argc == 3;
    const size_t count = sizeof(cases) / sizeof(cases[0]);
    unsigned int failures = 0;
    for (size_t i = 0; i < count; ++i) {
        const struct test_case *tc = &cases[i];
        uint64_t flags = UINT64_MAX;
        uint64_t actual = a64_add_flags(tc->a, tc->b, &flags);
        uint64_t expected = tc->sum;
        /* Deliberately corrupt one oracle, not the CPU operation. */
        if (injected && i == count - 1)
            expected ^= 1;
        const int passed = actual == expected && flags == tc->nzcv;
        failures += !passed;
        printf("ARM64_CASE {\"nonce\":\"%s\",\"name\":\"%s\","
               "\"a\":\"0x%016" PRIx64 "\",\"b\":\"0x%016" PRIx64 "\","
               "\"actual\":\"0x%016" PRIx64 "\",\"expected\":\"0x%016" PRIx64 "\","
               "\"nzcv\":\"0x%08" PRIx64 "\",\"expected_nzcv\":\"0x%08" PRIx64 "\","
               "\"passed\":%s}\n",
               argv[1], tc->name, tc->a, tc->b, actual, expected,
               flags, tc->nzcv, passed ? "true" : "false");
    }
    const int rc = failures ? 1 : 0;
    printf("ARM64_PAYLOAD_RESULT {\"nonce\":\"%s\",\"test\":\"isa_add_flags\","
           "\"cases\":%zu,\"failures\":%u,\"injected_failure\":%s,\"exit_code\":%d}\n",
           argv[1], count, failures, injected ? "true" : "false", rc);
    return rc;
}
