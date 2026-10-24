/* AAPCS64: x0=a, x1=b, x2=address at which to store NZCV; x0 returns sum. */
    .text
    .align 2
    .global a64_add_flags
    .type a64_add_flags, %function
a64_add_flags:
    adds x0, x0, x1
    mrs x3, nzcv
    str x3, [x2]
    ret
    .size a64_add_flags, .-a64_add_flags
    .section .note.GNU-stack,"",%progbits
