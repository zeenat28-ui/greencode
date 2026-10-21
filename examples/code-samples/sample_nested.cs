// Green Software Foundation Audit Sample: C# (.NET)
using System;
using System.Collections.Generic;

namespace GreenCode.Samples
{
    public class MatrixCalculator
    {
        public static long ComputeCubicComplexity(int[] a, int[] b, int[] c)
        {
            long accumulator = 0;

            for (int i = 0; i < a.Length; i++)
            {
                for (int j = 0; j < b.Length; j++)
                {
                    // Depth 3: Exponential thread CPU cycles
                    for (int k = 0; k < c.Length; k++)
                    {
                        accumulator += (long)a[i] * b[j] + c[k];
                    }
                }
            }

            return accumulator;
        }
    }
}

