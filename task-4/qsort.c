#include <stdio.h>

void swap(int* x, int* y)
{
  int tmp = *x;
  *x = *y;
  *y = tmp;
}


int partition(int* A, int l, int r)
{
  int pivot = A[r];
  int i = l-1;

  for (int j = l; j < r; j++)
  {
    if (A[j] < pivot)
    {
      i = i+1;
      swap(&A[i], &A[j]);
    }
  }

  i = i+1;
  swap(&A[i], &A[r]);

  return i;
}


void qsort(int* A, int l, int r)
{
  int k;

  if (l < r)
  {
    k = partition(A, l, r);
    qsort(A, l, k-1);
    qsort(A, k+1, r);
  }
}


int input(int *A)
{
  int size;

  if (fscanf(stdin, "%08x\n", &size) != 1)
  {
    return 0;
  }

  for (int i = 0; i < 10; i++)
  {
    if (fscanf(stdin, "%08x\n", A) != 1)
    {
      return size;
    }
    A++;
  }

  return size;
}


void output(int size, int* A)
{
  for (int i = 0; i < size; i++)
  {
    fprintf(stdout, "%08x\n", (unsigned int) A[i]);
  }
}


int main(void)
{
  int A[10];
  int size;

  size = input(A);
  qsort(A, 0, size-1);
  output(size, A);

  return 0;
}
