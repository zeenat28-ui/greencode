// Sample Java file with deep nested loops (O(N^3) complexity)
// Demonstrates Tree-sitter multi-language energy audit detection

public class TensorProcessor {
    public static long processBatch(int[] dimA, int[] dimB, int[] dimC) {
        long sum = 0;
        
        // ANTI-PATTERN: 3-level nested iteration
        for (int i = 0; i < dimA.length; i++) {
            for (int j = 0; j < dimB.length; j++) {
                for (int k = 0; k < dimC.length; k++) {
                    sum += (dimA[i] * dimB[j]) + dimC[k];
                }
            }
        }
        
        return sum;
    }
}
