// Green Software Foundation Audit Sample: Kotlin
package greencode.samples

class DataAggregator {
    fun aggregate(a: IntArray, b: IntArray, c: IntArray): Long {
        var total: Long = 0

        for (i in a) {
            for (j in b) {
                // Depth 3: O(N^3) CPU saturation
                for (k in c) {
                    total += (i.toLong() * j) + k
                }
            }
        }

        return total
    }
}

