// Sample Go file with deep nested loops (O(N^3) complexity)
// Demonstrates Tree-sitter multi-language energy audit detection

package main

func ComputeGrid(dimA []int, dimB []int, dimC []int) int {
	total := 0

	// ANTI-PATTERN: 3-level nested iteration
	for i := 0; i < len(dimA); i++ {
		for j := 0; j < len(dimB); j++ {
			for k := 0; k < len(dimC); k++ {
				total += (dimA[i] * dimB[j]) + dimC[k]
			}
		}
	}

	return total
}
