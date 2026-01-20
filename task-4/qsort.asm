###############################################################################
# Startup code
#
# Initializes the stack pointer, calls main, and stops simulation.
#
# Memory layout:
#   0 ... ~0x300  program
#   0x7EC       Top of stack, growing down
#   0x7FC       stdin/stdout
#
###############################################################################

.org 0x00
_start:
  ADDI sp, zero, 0x7EC
  ADDI fp, sp, 0

  # set saved registers to unique default values
  # to make checking for correct preservation easier
  LUI  s1, 0x11111
  ADDI s1, s1, 0x111
  ADD  s2, s1, s1
  ADD  s3, s2, s1
  ADD  s4, s3, s1
  ADD  s5, s4, s1
  ADD  s6, s5, s1
  ADD  s7, s6, s1
  ADD  s8, s7, s1
  ADD  s9, s8, s1
  ADD  s10, s9, s1
  ADD  s11, s10, s1

  JAL  ra, main
  EBREAK


##############################################################################
# void swap()   // a0 = &x, a1 = &y
##############################################################################
swap:
    LW   t0, 0(a0)
    LW   t1, 0(a1)
    SW   t1, 0(a0)
    SW   t0, 0(a1)
    JALR zero, 0(ra)


##############################################################################
# int partition()   // a0 = A, a1 = l, a2 = r → returns pivot index in a0
##############################################################################
partition:
    ADDI sp, sp, -32
    SW   ra, 28(sp)
    SW   s1, 20(sp)
    SW   s2, 16(sp)
    SW   s3, 12(sp)
    SW   s4, 8(sp)   # s4 base address A

    ADD  s4, a0, zero  # Save A into s4

    # compute A[r] addresss t0 = s4 + a2*4
    ADD  t0, a2, a2
    ADD  t0, t0, a2
    ADD  t0, t0, a2         # t0 = a2 * 4
    ADD  t0, s4, t0         # use saved A
    LW   s1, 0(t0)          # s1 = pivot

    ADDI s2, a1, -1         # s2 = i = l-1
    ADD  s3, a1, zero       # s3 = j = l

partition_loop:
    BGE  s3, a2, partition_end_loop

    # compute &A[j] → t1
    ADD  t1, s3, s3
    ADD  t1, t1, s3
    ADD  t1, t1, s3          # t1 = j*4
    ADD  t1, s4, t1          # Use A
    LW   t2, 0(t1)           # t2 = A[j]

    BGE  t2, s1, partition_no_swap

    ADDI s2, s2, 1         # i++

    # compute &A[i] → t3
    ADD  t3, s2, s2
    ADD  t3, t3, s2
    ADD  t3, t3, s2          # t3 = i*4
    ADD  t3, s4, t3          # use A

    # call swap(&A[i], &A[j])
    ADD  a0, t3, zero        # a0 = &A[i]
    ADD  a1, t1, zero        # a1 = &A[j]
    JAL  ra, swap

partition_no_swap:
    ADDI s3, s3, 1
    JAL  zero, partition_loop

partition_end_loop:
    ADDI s2, s2, 1        # i++

    #compute &A[i]
    ADD  t3, s2, s2
    ADD  t3, t3, s2
    ADD  t3, t3, s2
    ADD  t3, s4, t3         # use saved A (s4)

    # compute &A[r]
    ADD  t4, a2, a2
    ADD  t4, t4, a2
    ADD  t4, t4, a2
    ADD  t4, s4, t4         # use saved A (s4)

    # last swap
    ADD  a0, t3, zero
    ADD  a1, t4, zero
    JAL  ra, swap

    ADD  a0, s2, zero     # return i

    # Epilogue (remains the same)
    LW   ra, 28(sp)
    LW   s1, 20(sp)
    LW   s2, 16(sp)
    LW   s3, 12(sp)
    LW   s4, 8(sp)
    ADDI sp, sp, 32
    JALR zero, 0(ra)


###############################################################################
# Function: void qsort(int* A, int l, int r)
#
# Quicksort selects an element as pivot and partitions the other elements into two sub-arrays
# The sub-arrays are then sorted recursively
#
###############################################################################
qsort:
ADDI sp, sp, -32
    SW   ra, 28(sp)
    SW   s1, 20(sp)
    SW   s2, 16(sp)
    SW   s3, 12(sp)
    SW   s4, 8(sp)

    BGE  a1, a2, qsort_return       #if (l >= r) return

    ADD  s1, a0, zero       # s1 = A
    ADD  s2, a1, zero       # s2 = l
    ADD  s3, a2, zero       # s3 = r

    JAL  ra, partition
    ADD  s4, a0, zero 

    # qsort(A, l, k-1)
    ADD  a0, s1, zero
    ADD  a1, s2, zero
    ADDI a2, s4, -1
    BGE  a1, a2, qsort_skip_1    # recursion 1
    JAL  ra, qsort

qsort_skip_1:

    # qsort(A, k+1, r)
    ADD  a0, s1, zero
    ADDI a1, s4, 1
    ADD  a2, s3, zero
    BGE  a1, a2, qsort_return  #Jump to final return
    JAL  ra, qsort

qsort_return:
  # Epilogue
  LW   ra, 28(sp)
  LW   s1, 20(sp)
  LW   s2, 16(sp)
  LW   s3, 12(sp)
  LW   s4, 8(sp)
  ADDI sp, sp, 32
  JALR zero, 0(ra)

###############################################################################
# Function: int input(int *A)
#
# Reads at most 10 values from stdin to the input array.
#
# Input args:
# a0: address for array A
# Return value:
# a0: Number of read elements
#
###############################################################################
input:
  ADDI t0, a0, 0                  # Save a0
  LW   a0, 0x7fc(zero)            # Load size
  ADDI t1, zero, 10               # Maximum
  ADDI t2, zero, 0                # Loop counter
.before_input_loop:
  BGE  t2, t1, .after_input_loop  # Maximum values reached
  BGE  t2, a0, .after_input_loop  # All values read

  # Read from stdin in store in array A
  LW   t3, 0x7fc(zero)
  SW   t3, 0(t0)
  # Pointer increments
  ADDI t0, t0, 4

  ADDI t2, t2, 1                  # Increment loop counter
  JAL  zero, .before_input_loop   # Jump to loop begin

.after_input_loop:
  JALR zero, 0(ra)

###############################################################################
# Function: void output(int size, int* A)
#
# Prints input and output values to stdout
#
# Input args:
# a0: Number of elements
# a1: address for array A
#
###############################################################################
output:
.before_output_loop:
  BEQ  a0, zero, .after_output_loop
  # Load values
  LW   t0, 0(a1)
  # Output Values to stdout
  SW   t0, 0x7fc(zero)
  # Pointer increments
  ADDI a1, a1, 4
  # Decrement loop counter
  ADDI a0, a0, -1
  # jump to beginning
  JAL  zero, .before_output_loop

.after_output_loop:
  JALR zero, 0(ra)

###############################################################################
# Function: main
#
# Calls input, qsort, and output
#
###############################################################################
main:
  ADDI sp, sp, -64
  SW   ra, 60(sp)
  SW   s0, 56(sp)
  ADDI s0, sp, 64

  ADDI a0, s0, -52                # array A
  JAL  ra, input
  SW   a0, -56(s0)                # size

  ADDI a2, a0, -1                 # size - 1
  ADDI a1, zero, 0                # 0
  ADDI a0, s0, -52                # array A
  JAL  ra, qsort

  LW   a0, -56(s0)                # size
  ADDI a1, s0, -52                # array A
  JAL  ra, output

  ADDI a0, zero, 0                # return 0;

  LW   s0, 56(sp)
  LW   ra, 60(sp)
  ADDI sp, sp, 64
  JALR zero, 0(ra)
