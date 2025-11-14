"""
MURATURA FEM - Performance Optimizations Module

Implementa ottimizzazioni per migliorare performance:
- Sparse matrix storage
- Cached computations
- Parallel assembly
- Memory-efficient operations

Usage:
    from Material.optimizations import SparseMatrixAssembler, parallel_element_assembly

Author: MURATURA FEM Team
Version: 7.0.0-alpha
"""

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import spsolve
from typing import List, Tuple, Dict, Callable
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class SparseMatrixAssembler:
    """
    Assembler efficiente per matrici FEM sparse.

    Usa formato sparse per ridurre memoria e migliorare performance
    su sistemi grandi (>1000 DOF).

    Example:
        >>> assembler = SparseMatrixAssembler(ndof=1000)
        >>> assembler.add_element(element_stiffness, dof_indices)
        >>> K_global = assembler.get_matrix()
        >>> u = spsolve(K_global, F)
    """

    def __init__(self, ndof: int, sparse_threshold: int = 500):
        """
        Inizializza assembler.

        Args:
            ndof: Numero totale DOF del sistema
            sparse_threshold: Usa sparse se ndof > threshold
        """
        self.ndof = ndof
        self.use_sparse = ndof > sparse_threshold

        if self.use_sparse:
            self.K = lil_matrix((ndof, ndof))  # Efficient for construction
            logger.info(f"Using sparse matrix storage ({ndof} DOF)")
        else:
            self.K = np.zeros((ndof, ndof))
            logger.info(f"Using dense matrix storage ({ndof} DOF)")

        self.assembled = False

    def add_element(self, Ke: np.ndarray, dof_indices: List[int]):
        """
        Aggiungi contributo elemento alla matrice globale.

        Args:
            Ke: Matrice rigidezza elemento (n x n)
            dof_indices: Indici DOF globali dell'elemento
        """
        for i, gi in enumerate(dof_indices):
            for j, gj in enumerate(dof_indices):
                self.K[gi, gj] += Ke[i, j]

    def get_matrix(self):
        """
        Ottieni matrice assemblata (convertita a CSR per efficienza solve).

        Returns:
            scipy.sparse.csr_matrix o np.ndarray
        """
        if self.use_sparse and not self.assembled:
            self.K = self.K.tocsr()  # Convert to CSR for efficient arithmetic
            self.assembled = True
            logger.info(f"Matrix assembled: {self.K.nnz} non-zero elements "
                       f"({self.K.nnz/(self.ndof**2)*100:.2f}% density)")

        return self.K

    def solve(self, F: np.ndarray) -> np.ndarray:
        """
        Risolvi sistema K*u = F.

        Args:
            F: Vettore forze (ndof,)

        Returns:
            u: Vettore spostamenti (ndof,)
        """
        K = self.get_matrix()

        if self.use_sparse:
            u = spsolve(K, F)
            logger.info("Solved using sparse solver")
        else:
            u = np.linalg.solve(K, F)
            logger.info("Solved using dense solver")

        return u


@lru_cache(maxsize=128)
def cached_shape_functions(element_type: str, gauss_points: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Funzioni di forma e punti di Gauss cachate.

    Evita ricalcolo ripetuto per elementi dello stesso tipo.

    Args:
        element_type: 'quad4', 'tri3', etc.
        gauss_points: Numero punti Gauss

    Returns:
        (N, weights): Shape functions e pesi integrazione
    """
    if element_type == 'quad4':
        # 2x2 Gauss quadrature
        gp = 1.0 / np.sqrt(3.0)
        xi_eta = np.array([[-gp, -gp], [gp, -gp], [gp, gp], [-gp, gp]])
        weights = np.ones(4)
        return xi_eta, weights

    elif element_type == 'tri3':
        # 3-point Gauss for triangle
        xi_eta = np.array([[1/6, 1/6], [2/3, 1/6], [1/6, 2/3]])
        weights = np.array([1/6, 1/6, 1/6])
        return xi_eta, weights

    else:
        raise ValueError(f"Unknown element type: {element_type}")


class OptimizedStiffnessMatrix:
    """
    Calcolo ottimizzato matrici rigidezza elemento.

    Usa:
    - Caching di integrazioni comuni
    - Vectorizzazione operazioni
    - Pre-allocation memory
    """

    def __init__(self, element_type: str = 'quad4'):
        self.element_type = element_type
        self.gauss_points, self.weights = cached_shape_functions(element_type, 4)

    def compute_element_stiffness(self,
                                 nodes: np.ndarray,
                                 E: float,
                                 nu: float,
                                 thickness: float = 1.0) -> np.ndarray:
        """
        Calcola matrice rigidezza elemento con integrazione Gauss ottimizzata.

        Args:
            nodes: Coordinate nodi elemento (n x 2)
            E: Modulo elastico
            nu: Coefficiente Poisson
            thickness: Spessore

        Returns:
            Ke: Matrice rigidezza (n_dof x n_dof)
        """
        n_nodes = len(nodes)
        n_dof = n_nodes * 2

        # Pre-allocate
        Ke = np.zeros((n_dof, n_dof))

        # Constitutive matrix (plane stress)
        factor = E / (1 - nu**2)
        D = factor * np.array([
            [1, nu, 0],
            [nu, 1, 0],
            [0, 0, (1-nu)/2]
        ])

        # Numerical integration
        for gp, weight in zip(self.gauss_points, self.weights):
            # Shape function derivatives (implemented based on element_type)
            dN_dxi = self._shape_function_derivatives(gp)

            # Jacobian
            J = nodes.T @ dN_dxi
            detJ = np.linalg.det(J)

            # B matrix (strain-displacement)
            dN_dx = dN_dxi @ np.linalg.inv(J)
            B = self._compute_B_matrix(dN_dx)

            # Stiffness contribution
            Ke += B.T @ D @ B * detJ * weight * thickness

        return Ke

    def _shape_function_derivatives(self, xi_eta):
        """Derivate funzioni forma rispetto a coordinate naturali."""
        xi, eta = xi_eta

        if self.element_type == 'quad4':
            # Quad4 element
            dN_dxi = 0.25 * np.array([
                [-(1-eta), (1-eta), (1+eta), -(1+eta)],
                [-(1-xi), -(1+xi), (1+xi), (1-xi)]
            ])
            return dN_dxi.T
        else:
            raise NotImplementedError(f"Element {self.element_type} not implemented")

    def _compute_B_matrix(self, dN_dx):
        """Matrice strain-displacement."""
        n_nodes = dN_dx.shape[0]
        B = np.zeros((3, n_nodes * 2))

        for i in range(n_nodes):
            B[0, 2*i] = dN_dx[i, 0]      # ε_xx = ∂u/∂x
            B[1, 2*i+1] = dN_dx[i, 1]    # ε_yy = ∂v/∂y
            B[2, 2*i] = dN_dx[i, 1]      # γ_xy = ∂u/∂y + ∂v/∂x
            B[2, 2*i+1] = dN_dx[i, 0]

        return B


def parallel_element_assembly(elements: List[Dict],
                              assembler_func: Callable,
                              n_workers: int = 4) -> List[Tuple]:
    """
    Assembly parallelo matrici elemento.

    Args:
        elements: Lista dati elementi
        assembler_func: Funzione che calcola Ke per elemento
        n_workers: Numero workers paralleli

    Returns:
        List of (Ke, dof_indices) tuples

    Note: Requires pickle-able function (use module-level function)
    """
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(assembler_func, elements))

    logger.info(f"Assembled {len(elements)} elements using {n_workers} workers")
    return results


class MemoryEfficientStorage:
    """
    Storage efficiente per grandi quantità di dati analisi.

    Usa:
    - Memoria condivisa per arrays grandi
    - Compression per risultati storici
    - Streaming per output
    """

    def __init__(self, use_compression: bool = True):
        self.use_compression = use_compression
        self.data = {}

    def store_results(self, key: str, data: np.ndarray):
        """Store results with optional compression."""
        if self.use_compression and data.nbytes > 1024 * 1024:  # > 1 MB
            import gzip
            import pickle
            compressed = gzip.compress(pickle.dumps(data))
            self.data[key] = ('compressed', compressed)
            logger.info(f"Stored {key}: {len(compressed)/1024:.1f} KB (compressed from {data.nbytes/1024:.1f} KB)")
        else:
            self.data[key] = ('raw', data)

    def retrieve_results(self, key: str) -> np.ndarray:
        """Retrieve results (decompress if needed)."""
        storage_type, data = self.data[key]

        if storage_type == 'compressed':
            import gzip
            import pickle
            return pickle.loads(gzip.decompress(data))
        else:
            return data


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def estimate_memory_usage(ndof: int, sparse_density: float = 0.05) -> Dict[str, float]:
    """
    Stima uso memoria per modello FEM.

    Args:
        ndof: Numero DOF
        sparse_density: Densità matrice sparse (default 5%)

    Returns:
        Dict con stime memoria in MB
    """
    # Dense matrix: ndof x ndof x 8 bytes (float64)
    dense_mb = (ndof * ndof * 8) / (1024 * 1024)

    # Sparse matrix: only non-zero elements
    nnz = int(ndof * ndof * sparse_density)
    sparse_mb = (nnz * (8 + 4 + 4)) / (1024 * 1024)  # value + row_idx + col_idx

    return {
        'dense_matrix_mb': dense_mb,
        'sparse_matrix_mb': sparse_mb,
        'memory_saved_mb': dense_mb - sparse_mb,
        'compression_ratio': dense_mb / sparse_mb if sparse_mb > 0 else 0
    }


def print_optimization_recommendations(ndof: int):
    """
    Stampa raccomandazioni ottimizzazione per modello.

    Args:
        ndof: Numero DOF del modello
    """
    print(f"\n{'='*70}")
    print(f"PERFORMANCE OPTIMIZATION RECOMMENDATIONS ({ndof} DOF)")
    print(f"{'='*70}\n")

    mem = estimate_memory_usage(ndof)

    print(f"Memory Analysis:")
    print(f"  Dense storage:  {mem['dense_matrix_mb']:.1f} MB")
    print(f"  Sparse storage: {mem['sparse_matrix_mb']:.1f} MB")
    print(f"  💾 Memory saved: {mem['memory_saved_mb']:.1f} MB ({mem['compression_ratio']:.1f}x)")

    if ndof > 500:
        print(f"\n✅ RECOMMENDED: Use SparseMatrixAssembler")
        print(f"   - {mem['compression_ratio']:.1f}x memory reduction")
        print(f"   - Faster solve for large systems")

    if ndof > 2000:
        print(f"\n✅ RECOMMENDED: Enable parallel assembly")
        print(f"   - 2-4x speedup expected")
        print(f"   - Use ProcessPoolExecutor")

    if mem['dense_matrix_mb'] > 1000:
        print(f"\n⚠️  WARNING: Large memory footprint ({mem['dense_matrix_mb']:.0f} MB)")
        print(f"   - Consider model reduction")
        print(f"   - Use substructuring")

    print()


if __name__ == "__main__":
    # Demo usage
    print("MURATURA FEM - Performance Optimizations Demo\n")

    # Test sparse assembler
    print("1. Sparse Matrix Assembler Demo:")
    assembler = SparseMatrixAssembler(ndof=1000)
    print(f"   Created assembler for 1000 DOF")

    # Optimization recommendations
    print("\n2. Optimization Recommendations:")
    print_optimization_recommendations(5000)
