// Sample C++ file with deep nested loops (O(N^3) complexity)
// Demonstrates Tree-sitter multi-language energy audit detection

#include <vector>
#include <iostream>

long long computeTensors(const std::vector<int>& a, const std::vector<int>& b, const std::vector<int>& c) {
    long long totalEnergyDrain = 0;
    
    // ANTI-PATTERN: 3-level nested iteration
    for (size_t i = 0; i < a.size(); ++i) {
        for (size_t j = 0; j < b.size(); ++j) {
            for (size_t k = 0; k < c.size(); ++k) {
                totalEnergyDrain += (a[i] * b[j]) + c[k];
            }
        }
    }
    
    return totalEnergyDrain;
}
