#include <stdio.h>

//-----------------------------------------------------------------------------
// RISC-V Register set
const size_t zero = 0;
size_t a0, a1;                      // fn args or return args
size_t a2, a3, a4, a5, a6, a7;      // fn args
size_t t0, t1, t2, t3, t4, t5, t6;  // temporaries
// Callee saved registers, must be stacked befor using it in a function!
size_t s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11;
//-----------------------------------------------------------------------------

void swap(void)
{
    t0 = *(int*)a0;
    t1 = *(int*)a1;
    *(int*)a0 = t1;
    *(int*)a1 = t0;
}


void partition(void)
{
    // arguments a1 = l, a2 = r, s1 = pivot value, s2 (i), s3 (j), s4 (base A address), s_int = index/value
    int s1, s2, s3; // make int otherwise Errors
    s4 = a0;
    
    // copy arguments into registers
    s2 = a1 - 1;
    s3 = a1;

    // &A[r] (t0 = s4 + a2*4)
    t0 = a2;
    t0 = t0 + t0;
    t0 = t0 + t0;  
    t0 = s4 + t0;
    s1 = *(int*)t0;  // s1 = pivot = A[r]

partition_loop:
    
    if (s3 >= (int)a2) goto partition_end;

    //&A[j] (t4 = s4 + s3*4)
    t4 = s3;
    t4 = t4 + t4;
    t4 = t4 + t4;
    t4 = s4 + t4;
    t5 = *(int*)t4;

    // if (A[j] >= pivot)
    if ((int)t5 >= s1) goto no_swap; 

    s2 = s2 + 1;

    //&A[i] (t5 = s4 + s2*4)
    t5 = s2;
    t5 = t5 + t5;
    t5 = t5 + t5;
    t5 = s4 + t5;

    // swap(A[i], A[j])
    a0 = t5;
    a1 = t4;
    swap(); 
    
no_swap:
    s3 = s3 + 1;      // j++
    goto partition_loop;

partition_end:
    s2 = s2 + 1;        // i++ (last increment)

    // last swap()
    t5 = (size_t)s2;
    t5 = t5 + t5;
    t5 = t5 + t5;
    t5 = s4 + t5;

    t6 = a2;
    t6 = t6 + t6;
    t6 = t6 + t6;
    t6 = s4 + t6;

    a0 = t5;
    a1 = t6;
    swap();

    s4 = s4;      // base address A

    a0 = s2;   // return final pivot index (i)
}


void qsort() // void qsort(int* A, int l, int r)
{
    // arguments are a0 = A, a1 = l, a2 = r
    if (a1 >= a2) goto qsort_done;

    //save arguments to callee registers (s1=A, s2=l, s3=r)
    s1 = a0; 
    int s2 = a1;
    int s3 = a2; 

    partition();
    
    // s4 = k = ret pivot index => must save at all cost
    s4 = a0;

    // first recursion qsort(A, l, k-1)
    a0 = s1;
    a1 = s2;
    a2 = s4 - 1; 
    
    if ((int)a1 >= (int)a2) goto qsort_skip_1; 
    
    qsort(); 

qsort_skip_1:;
    
    // second recursion qsort(A, k+1, r)
    a0 = s1;
    a1 = s4 + 1;
    a2 = s3;     

    if ((int)a1 >= (int)a2) goto qsort_done;

    qsort(); 

qsort_done:;

}

void input(void)
{
    // Read size
    t0 = a0; // Save a0
    a0 = fscanf(stdin, "%08x\n", (int*)&t1);
    t4 = 1;
    if (a0 == t4) goto input_continue;
    // Early exit
    a0 = 0;
    return;

input_continue:
    t4 = 1;
    t5 = 10;
input_loop_begin:
    if(t5 == 0) goto after_input_loop;
    a0 = fscanf(stdin, "%08x\n", (int*)&t2);
    if(a0 == t4) goto continue_read;
    // Exit, because read was not successful
    a0 = t1;
    return;
continue_read:
    *(int*)t0 = t2;
    // Pointer increment for next iteration
    t0 = t0 + 4;
    // Loop counter decrement
    t5 = t5 - 1;
    goto input_loop_begin;

after_input_loop:
    a0 = t1;
    return;
}


void output(void)
{
before_output_loop:
    if (a0 == 0) goto after_output_loop;

    fprintf(stdout, "%08x\n", (unsigned int)*(int*)a1);

    // Pointer increment for next iteration
    a1 = a1 + 4;
    // Decrement loop counter
    a0 = a0 - 1;
    goto before_output_loop;

after_output_loop:
    return;
}


int main(void)
{
  int A[10];
  int size;

  a0 = (size_t) A;
  input();
  size = a0;

  a0 = (size_t) A;
  a1 = 0;
  a2 = size - 1;
  qsort();

  a0 = size;
  a1 = (size_t) A;
  output();

  return 0;
}
