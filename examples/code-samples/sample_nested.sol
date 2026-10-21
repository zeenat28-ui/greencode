// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Green Software Foundation Audit Sample: Solidity Smart Contract
// Gas-inefficient cubic loop iterations causing severe computational waste
contract EnergyVault {
    uint256 public totalCompute;

    function processBatch(uint256[] memory a, uint256[] memory b, uint256[] memory c) public {
        for (uint256 i = 0; i < a.length; i++) {
            for (uint256 j = 0; j < b.length; j++) {
                // Depth 3: Critical gas burn & node validator thermal dissipation
                for (uint256 k = 0; k < c.length; k++) {
                    totalCompute += (a[i] * b[j]) + c[k];
                }
            }
        }
    }
}

