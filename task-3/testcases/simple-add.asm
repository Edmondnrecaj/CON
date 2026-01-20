# division example with edge cases

    .org 0x00
    ADDI x1, x0, 0x0000020
    ADDI x2, x0, 0x0000030

    ADD x5, x2, x1
    ADD x6, x1, x0
    ADD x7, x1, x2
    ADD x0, x1, x2
    
    # Write results to stdout
    SW x5, 0x7fc(x0)
    SW x6, 0x7fc(x0)
    SW x7, 0x7fc(x0)
    SW x0, 0x7fc(x0)

    EBREAK

