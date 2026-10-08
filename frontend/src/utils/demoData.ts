import { ScanResult, GitHubRepo } from '../types';

export const DEMO_REPOSITORIES: GitHubRepo[] = [
  {
    full_name: 'demo-org/ecommerce-django-api',
    name: 'ecommerce-django-api',
    owner: 'demo-org',
    default_branch: 'main',
    language: 'Python',
    description: 'High-throughput checkout service with quadratic ORM lookups and blocking database loops.',
    size_kb: 4280,
    private: false,
    fork: false,
    archived: false,
    stars: 342,
    forks: 48,
    open_issues: 7,
    updated_at: new Date().toISOString(),
    url: 'https://github.com/demo-org/ecommerce-django-api',
  },
  {
    full_name: 'demo-org/telemetry-fastapi-service',
    name: 'telemetry-fastapi-service',
    owner: 'demo-org',
    default_branch: 'main',
    language: 'Python',
    description: 'High-frequency telemetry pipeline with unindexed stream queries and synchronous I/O bottlenecks.',
    size_kb: 2150,
    private: false,
    fork: false,
    archived: false,
    stars: 189,
    forks: 23,
    open_issues: 3,
    updated_at: new Date().toISOString(),
    url: 'https://github.com/demo-org/telemetry-fastapi-service',
  },
  {
    full_name: 'demo-org/transformers-llm-pipeline',
    name: 'transformers-llm-pipeline',
    owner: 'demo-org',
    default_branch: 'main',
    language: 'Python',
    description: 'PyTorch LLM embedding pipeline with unquantized FP32 forward passes and missing inference_mode.',
    size_kb: 5120,
    private: false,
    fork: false,
    archived: false,
    stars: 521,
    forks: 74,
    open_issues: 5,
    updated_at: new Date().toISOString(),
    url: 'https://github.com/demo-org/transformers-llm-pipeline',
  },
];

export const DEMO_SCAN_DATA: Record<string, ScanResult> = {
  'demo-org/ecommerce-django-api': {
    repo_path: 'demo-org/ecommerce-django-api',
    full_name: 'demo-org/ecommerce-django-api',
    ref: 'main',
    default_branch: 'main',
    source: 'github',
    is_github: true,
    total_files: 42,
    total_lines: 8450,
    green_score: 68,
    total_violations: 4,
    energy_wh: 0.185,
    carbon_g: 0.0398,
    violation_breakdown: {
      NESTED_LOOPS: 2,
      REDUNDANT_COMPUTATION: 1,
      BLOCKING_IO: 1,
    },
    languages_breakdown: {
      Python: 36,
      SQL: 4,
      YAML: 2,
    },
    violations: [
      {
        id: 101,
        file_path: 'checkout/inventory.py',
        relative_path: 'checkout/inventory.py',
        language: 'python',
        line_number: 48,
        end_line_number: 62,
        violation_type: 'NESTED_LOOPS_DEPTH_3+',
        title: 'Quadratic O(N²) Nested Loop in Order Processing',
        severity: 'HIGH',
        deduction: 15,
        gsf_pattern: 'GSF-001 Algorithmic Complexity',
        description: 'Nested loop over order line items and warehouse inventory records causes quadratic O(N*M) CPU cycles on large baskets.',
        suggested_fix: 'Convert inventory records to a pre-indexed dictionary/hash map for O(1) lookup and O(N) total runtime.',
        snippet: `def match_warehouse_stock(order_items, warehouse_records):
    matches = []
    for item in order_items:
        for stock in warehouse_records:
            if stock.sku == item.sku and stock.quantity >= item.quantity:
                matches.append({"item": item, "location": stock.bay})
    return matches`,
        context_code: `def match_warehouse_stock(order_items, warehouse_records):
    matches = []
    for item in order_items:
        for stock in warehouse_records:
            if stock.sku == item.sku and stock.quantity >= item.quantity:
                matches.append({"item": item, "location": stock.bay})
    return matches`,
        rule_code: 'AST_NESTED_LOOP_QUADRATIC',
      },
      {
        id: 102,
        file_path: 'checkout/pricing.py',
        relative_path: 'checkout/pricing.py',
        language: 'python',
        line_number: 114,
        end_line_number: 126,
        violation_type: 'HIDDEN_ITERATIVE_COMPUTATION',
        title: 'Redundant In-Loop Discount Recalculation',
        severity: 'MEDIUM',
        deduction: 10,
        gsf_pattern: 'GSF-002 Redundant Computation',
        description: 'Global promotional discount rate is recalculated repeatedly inside the per-item calculation loop instead of being hoisted.',
        suggested_fix: 'Hoist constant promotional calculations outside the iteration loop.',
        snippet: `def calculate_cart_totals(items, promo_code):
    total = 0.0
    for item in items:
        discount = lookup_campaign_discount(promo_code)
        tax = compute_regional_tax(item.category)
        total += (item.price * (1 - discount)) * (1 + tax)
    return total`,
        context_code: `def calculate_cart_totals(items, promo_code):
    total = 0.0
    for item in items:
        discount = lookup_campaign_discount(promo_code)
        tax = compute_regional_tax(item.category)
        total += (item.price * (1 - discount)) * (1 + tax)
    return total`,
        rule_code: 'AST_REDUNDANT_LOOP_CALL',
      },
      {
        id: 103,
        file_path: 'analytics/customer_insights.py',
        relative_path: 'analytics/customer_insights.py',
        language: 'python',
        line_number: 82,
        end_line_number: 95,
        violation_type: 'LINEAR_LOOKUP_IN_LOOP',
        title: 'Unvectorized Matrix Multiplications in Cart Recommendation',
        severity: 'MEDIUM',
        deduction: 7,
        gsf_pattern: 'GSF-003 Vectorization',
        description: 'Iterative pairwise matrix multiplication in Python loop instead of vectorized NumPy dot product.',
        suggested_fix: 'Vectorize similarity calculation using NumPy dot product or batched tensor arithmetic.',
        snippet: `def compute_similarity(vector_a, matrix_b):
    scores = []
    for row in matrix_b:
        dot = 0.0
        for i in range(len(vector_a)):
            dot += vector_a[i] * row[i]
        scores.append(dot)
    return scores`,
        context_code: `def compute_similarity(vector_a, matrix_b):
    scores = []
    for row in matrix_b:
        dot = 0.0
        for i in range(len(vector_a)):
            dot += vector_a[i] * row[i]
        scores.append(dot)
    return scores`,
        rule_code: 'AST_UNVECTORIZED_ARRAY_LOOP',
      },
    ],
    file_results: [
      {
        file_path: 'checkout/inventory.py',
        relative_path: 'checkout/inventory.py',
        language: 'Python',
        lines_count: 142,
        green_score: 65,
        violations: [],
        total_deductions: 15,
      },
      {
        file_path: 'checkout/pricing.py',
        relative_path: 'checkout/pricing.py',
        language: 'Python',
        lines_count: 220,
        green_score: 70,
        violations: [],
        total_deductions: 10,
      },
      {
        file_path: 'analytics/customer_insights.py',
        relative_path: 'analytics/customer_insights.py',
        language: 'Python',
        lines_count: 310,
        green_score: 75,
        violations: [],
        total_deductions: 7,
      },
    ],
  },
  'demo-org/transformers-llm-pipeline': {
    repo_path: 'demo-org/transformers-llm-pipeline',
    full_name: 'demo-org/transformers-llm-pipeline',
    ref: 'main',
    default_branch: 'main',
    source: 'github',
    is_github: true,
    total_files: 28,
    total_lines: 6240,
    green_score: 59,
    total_violations: 3,
    energy_wh: 0.420,
    carbon_g: 0.0903,
    violation_breakdown: {
      UNQUANTIZED_FP32_TENSORS: 1,
      MISSING_INFERENCE_MODE: 1,
      UNBATCHED_TOKEN_STREAM: 1,
    },
    languages_breakdown: {
      Python: 24,
      C: 2,
      Shell: 2,
    },
    violations: [
      {
        id: 201,
        file_path: 'models/inference_engine.py',
        relative_path: 'models/inference_engine.py',
        language: 'python',
        line_number: 34,
        end_line_number: 48,
        violation_type: 'HIDDEN_ITERATIVE_COMPUTATION',
        title: 'Unquantized FP32 Forward Pass in Model Serving',
        severity: 'CRITICAL',
        deduction: 20,
        gsf_pattern: 'GSF-004 AI/LLM Precision Efficiency',
        description: 'Large language model inference runs with full 32-bit floating point weights instead of INT8/FP8 quantization, 4x inflating memory bus power consumption.',
        suggested_fix: 'Apply post-training dynamic INT8 quantization with torch.quantization.quantize_dynamic.',
        snippet: `def generate_embeddings(model, token_batches):
    embeddings = []
    # Running full FP32 without quantization
    for batch in token_batches:
        out = model.forward(batch.to(torch.float32))
        embeddings.append(out.detach().cpu())
    return embeddings`,
        context_code: `def generate_embeddings(model, token_batches):
    embeddings = []
    for batch in token_batches:
        out = model.forward(batch.to(torch.float32))
        embeddings.append(out.detach().cpu())
    return embeddings`,
        rule_code: 'AST_AI_FP32_PRECISION_WASTE',
      },
      {
        id: 202,
        file_path: 'models/inference_engine.py',
        relative_path: 'models/inference_engine.py',
        language: 'python',
        line_number: 62,
        end_line_number: 75,
        violation_type: 'HIDDEN_ITERATIVE_COMPUTATION',
        title: 'Missing torch.inference_mode() Context Manager',
        severity: 'HIGH',
        deduction: 14,
        gsf_pattern: 'GSF-005 Autograd Graph Overhead',
        description: 'Executing neural net inference without inference_mode() constructs internal computation graphs in GPU memory, wasting 35% surplus memory.',
        suggested_fix: 'Wrap forward passes in "with torch.inference_mode():" to deactivate PyTorch autograd tracking.',
        snippet: `def batch_predict(classifier, inputs):
    # Missing torch.inference_mode() causes autograd graph retention
    logits = classifier(inputs)
    probabilities = torch.softmax(logits, dim=-1)
    return probabilities.tolist()`,
        context_code: `def batch_predict(classifier, inputs):
    logits = classifier(inputs)
    probabilities = torch.softmax(logits, dim=-1)
    return probabilities.tolist()`,
        rule_code: 'AST_AI_MISSING_INFERENCE_MODE',
      },
      {
        id: 203,
        file_path: 'serving/token_stream.py',
        relative_path: 'serving/token_stream.py',
        language: 'python',
        line_number: 95,
        end_line_number: 110,
        violation_type: 'NESTED_LOOPS_DEPTH_3+',
        title: 'Unbatched Serial Token Generation Loop',
        severity: 'MEDIUM',
        deduction: 7,
        gsf_pattern: 'GSF-006 Tensor Batching',
        description: 'Iterative single-item token generation leaves GPU compute cores 80% idle while sustaining 140W static power draw.',
        suggested_fix: 'Implement dynamic batching and continuous key-value cache paging.',
        snippet: `def stream_tokens_serial(requests, model):
    responses = []
    for req in requests:
        for prompt in req.prompts:
            for step in range(req.max_tokens):
                tok = model.next_token(prompt)
                responses.append(tok)
    return responses`,
        context_code: `def stream_tokens_serial(requests, model):
    responses = []
    for req in requests:
        for prompt in req.prompts:
            for step in range(req.max_tokens):
                tok = model.next_token(prompt)
                responses.append(tok)
    return responses`,
        rule_code: 'AST_AI_UNBATCHED_TOKEN_STREAM',
      },
    ],
    file_results: [
      {
        file_path: 'models/inference_engine.py',
        relative_path: 'models/inference_engine.py',
        language: 'Python',
        lines_count: 240,
        green_score: 55,
        violations: [],
        total_deductions: 34,
      },
      {
        file_path: 'serving/token_stream.py',
        relative_path: 'serving/token_stream.py',
        language: 'Python',
        lines_count: 180,
        green_score: 65,
        violations: [],
        total_deductions: 7,
      },
    ],
  },
};
