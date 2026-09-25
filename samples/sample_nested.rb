# Green Software Foundation Audit Sample: Ruby
# Algorithmic Complexity: O(N^3) iteration cascade

def compute_cube(a, b, c)
  total = 0
  for i in a
    for j in b
      # Depth 3: Runaway CPU execution cycles
      for k in c
        total += i * j + k
      end
    end
  end
  total
end

