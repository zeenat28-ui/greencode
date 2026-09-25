// Sample JavaScript file with deep nested loops (O(N^3) complexity)
// Demonstrates Tree-sitter multi-language energy audit detection

function processMatrixBatch(matrixA, matrixB, matrixC) {
    let processedCount = 0;
    
    // ANTI-PATTERN: 3-level nested iteration
    for (let i = 0; i < matrixA.length; i++) {
        for (let j = 0; j < matrixB.length; j++) {
            for (let k = 0; k < matrixC.length; k++) {
                processedCount += (matrixA[i] * matrixB[j]) + matrixC[k];
            }
        }
    }
    
    return processedCount;
}

module.exports = { processMatrixBatch };
