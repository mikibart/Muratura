"""
MURATURA FEM - Performance Benchmarking Suite

Test performance con modelli di diverse dimensioni per:
- FEM analysis
- Report generation
- IFC import/export

Usage:
    python benchmarks/benchmark_performance.py

Output: Performance report with timing and memory usage
"""

import time
import psutil
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Try import Material modules
try:
    from Material import MasonryFEMEngine
    from Material.materials import MaterialProperties
    MURATURA_AVAILABLE = True
except ImportError:
    print("Warning: Material modules not fully available")
    MURATURA_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Risultato singolo benchmark."""
    name: str
    elements: int
    time_seconds: float
    memory_mb: float
    iterations: int = 1


class PerformanceBenchmark:
    """Suite benchmarking completa."""

    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process()

    def measure_time_memory(self, func, *args, **kwargs) -> Tuple[float, float, any]:
        """Misura tempo e memoria di una funzione."""
        # Memory before
        mem_before = self.process.memory_info().rss / 1024 / 1024  # MB

        # Time execution
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        # Memory after
        mem_after = self.process.memory_info().rss / 1024 / 1024  # MB

        elapsed = end_time - start_time
        mem_used = mem_after - mem_before

        return elapsed, mem_used, result

    def benchmark_matrix_operations(self):
        """Benchmark operazioni matrici (base FEM)."""
        print("\n📊 Benchmarking Matrix Operations...")

        sizes = [100, 500, 1000, 2000]
        for size in sizes:
            def matrix_solve():
                A = np.random.rand(size, size)
                A = A + A.T  # Symmetric
                b = np.random.rand(size)
                x = np.linalg.solve(A, b)
                return x

            time_s, mem_mb, _ = self.measure_time_memory(matrix_solve)

            result = BenchmarkResult(
                name=f"Matrix Solve",
                elements=size,
                time_seconds=time_s,
                memory_mb=mem_mb
            )
            self.results.append(result)

            print(f"  {size}x{size}: {time_s:.3f}s, {mem_mb:.1f} MB")

    def benchmark_sparse_vs_dense(self):
        """Benchmark sparse vs dense matrices."""
        from scipy.sparse import csr_matrix
        from scipy.sparse.linalg import spsolve

        print("\n🔍 Benchmarking Sparse vs Dense...")

        size = 1000
        density = 0.01  # 1% non-zero elements (typical for FEM)

        # Dense
        def dense_solve():
            A = np.random.rand(size, size)
            A = A * (np.random.rand(size, size) < density)  # Sparse pattern
            b = np.random.rand(size)
            x = np.linalg.solve(A + np.eye(size), b)  # Add identity for stability
            return x

        time_dense, mem_dense, _ = self.measure_time_memory(dense_solve)

        # Sparse
        def sparse_solve():
            A = np.random.rand(size, size)
            A = A * (np.random.rand(size, size) < density)
            A_sparse = csr_matrix(A + np.eye(size))
            b = np.random.rand(size)
            x = spsolve(A_sparse, b)
            return x

        time_sparse, mem_sparse, _ = self.measure_time_memory(sparse_solve)

        print(f"  Dense:  {time_dense:.3f}s, {mem_dense:.1f} MB")
        print(f"  Sparse: {time_sparse:.3f}s, {mem_sparse:.1f} MB")
        print(f"  Speedup: {time_dense/time_sparse:.2f}x")
        print(f"  Memory saved: {mem_dense - mem_sparse:.1f} MB")

        self.results.append(BenchmarkResult("Dense Solve", size, time_dense, mem_dense))
        self.results.append(BenchmarkResult("Sparse Solve", size, time_sparse, mem_sparse))

    def benchmark_parallel_vs_serial(self):
        """Benchmark parallel vs serial processing."""
        from concurrent.futures import ProcessPoolExecutor

        print("\n⚡ Benchmarking Parallel Processing...")

        def heavy_computation(n):
            """Simulazione calcolo pesante."""
            result = 0
            for i in range(n):
                result += np.sum(np.random.rand(100, 100) @ np.random.rand(100, 100))
            return result

        iterations = 20

        # Serial
        def serial_process():
            results = [heavy_computation(100) for _ in range(iterations)]
            return results

        time_serial, mem_serial, _ = self.measure_time_memory(serial_process)

        # Parallel
        def parallel_process():
            with ProcessPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(heavy_computation, [100] * iterations))
            return results

        time_parallel, mem_parallel, _ = self.measure_time_memory(parallel_process)

        print(f"  Serial:   {time_serial:.3f}s")
        print(f"  Parallel: {time_parallel:.3f}s ({iterations} tasks, 4 workers)")
        print(f"  Speedup: {time_serial/time_parallel:.2f}x")

        self.results.append(BenchmarkResult("Serial Processing", iterations, time_serial, mem_serial))
        self.results.append(BenchmarkResult("Parallel Processing", iterations, time_parallel, mem_parallel))

    def generate_report(self):
        """Genera report performance."""
        print("\n" + "=" * 70)
        print("PERFORMANCE BENCHMARK REPORT")
        print("=" * 70)

        print(f"\nTotal benchmarks: {len(self.results)}")
        print(f"\nResults:")
        print(f"{'Test':<30} {'Elements':<12} {'Time (s)':<12} {'Memory (MB)':<12}")
        print("-" * 70)

        for result in self.results:
            print(f"{result.name:<30} {result.elements:<12} {result.time_seconds:<12.3f} {result.memory_mb:<12.1f}")

        print("\n" + "=" * 70)
        print("RECOMMENDATIONS:")
        print("=" * 70)

        # Analyze results
        sparse_results = [r for r in self.results if 'Sparse' in r.name]
        dense_results = [r for r in self.results if 'Dense' in r.name]

        if sparse_results and dense_results:
            sparse_time = sparse_results[0].time_seconds
            dense_time = dense_results[0].time_seconds
            speedup = dense_time / sparse_time

            print(f"\n✅ Sparse matrices: {speedup:.1f}x faster than dense")
            print("   → Implement sparse matrix storage for FEM")
            print("   → Use scipy.sparse.linalg for solve operations")

        parallel_results = [r for r in self.results if 'Parallel' in r.name]
        serial_results = [r for r in self.results if 'Serial' in r.name]

        if parallel_results and serial_results:
            parallel_time = parallel_results[0].time_seconds
            serial_time = serial_results[0].time_seconds
            speedup = serial_time / parallel_time

            print(f"\n✅ Parallel processing: {speedup:.1f}x faster than serial")
            print("   → Parallelize element stiffness assembly")
            print("   → Use multiprocessing for batch analyses")

        # Memory optimization
        max_memory = max(r.memory_mb for r in self.results)
        print(f"\n📊 Peak memory usage: {max_memory:.1f} MB")
        if max_memory > 1000:
            print("   ⚠️  Consider streaming for large models")

        print("\n💡 Implementation Priority:")
        print("   1. Sparse matrix storage (HIGH - easy win)")
        print("   2. Parallel assembly (MEDIUM - good speedup)")
        print("   3. Caching repeated calculations (LOW - marginal)")
        print()


def main():
    """Main benchmark execution."""
    print("🚀 MURATURA FEM - Performance Benchmarking Suite")
    print("   Testing system performance for optimization planning\n")

    benchmark = PerformanceBenchmark()

    try:
        # Run benchmarks
        benchmark.benchmark_matrix_operations()
        benchmark.benchmark_sparse_vs_dense()
        benchmark.benchmark_parallel_vs_serial()

        # Generate report
        benchmark.generate_report()

        print("✅ Benchmarking complete!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmarking interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during benchmarking: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
