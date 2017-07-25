
# coding: utf-8

import scipy as sp
import scipy.sparse.linalg
import numpy as np
import seaborn as sns
from itertools import permutations
from cvxpy import *

eigs = sp.sparse.linalg.eigs

def find_permutation_Theta(Theta, Theta_exp):
    '''
    function to find permutation of Theta cols which minimize
    Frobenius norm:

        || Theta - Theta_exp ||

    the output is the relative error, optimal Theta_exp

    returns
    _______________________________________________
    relative error: float
    min_theta: nd.array with shape == Theta.shape
    '''

    assert Theta.shape == Theta_exp.shape, "Theta.shape != Theta_exp.shape"
    error = np.inf
    min_theta = np.zeros_like(Theta_exp)
    
    for perm in permutations(range(Theta.shape[1])):
        temple_error = np.linalg.norm(Theta - Theta_exp[:, perm], ord='fro')
        if temple_error < error:
            error = temple_error
            min_theta = Theta_exp[:, perm]
            
    return (error / np.linalg.norm(Theta, ord='fro'), min_theta)


def find_permutation_B(B, B_exp):
    '''
    function to find permutation of Theta cols and rows
    which minimize Frobenius norm:

        || B - B_exp ||

    the output is the relative error, optimal B_exp

    returns
    _______________________________________________
    relative error: float
    min_B: nd.array with shape == B.shape
    '''

    assert B.shape == B_exp.shape, "B.shape != B_exp.shape"
    error = np.inf
    min_B = np.zeros_like(B_exp)
    
    for perm in permutations(range(B.shape[1])):
        perm_B = B_exp[:, perm]
        perm_B = perm_B[perm, :]
        temple_error = np.linalg.norm(B - perm_B, ord='fro')
        if temple_error < error:
            error = temple_error
            min_B = perm_B
            
    return (error, min_B)


def generate_graph(n, frac, p, q, **kwargs):
    '''
    function to generate graph with 2 communities
    p is a probability of the edge inside clusters
    q is a probability of the edge between clusters
    returns
    _______________________________________________
    P, A, true_comms
    '''
    if ("random_state" in kwargs):
        seed = kwargs["random_state"]
        np.random.seed(seed = seed)

    s1 = int(n*frac)
    s2 = n - s1
    g_in1 = p * np.ones((s1, s1))
    g_in2 = p * np.ones((s2, s2))
    g_out1 = q * np.ones((s1, s2))
    g_out2 = q * np.ones((s2, s1))

    P = np.bmat([[g_in1, g_out1], [g_out2, g_in2]])
    A = 1.0 * (np.random.rand(n, n) < P)
    true_comm = np.concatenate([ np.ones((s1, 1)), - np.ones((s2, 1))]).T

    cluster_1 = []
    cluster_2 = []
    for arg, node in enumerate(true_comm[0]):
        if node == 1:
            cluster_1.append(arg)
        else:
            cluster_2.append(arg)
    true_comm = [cluster_1, cluster_2]
    return P, A, true_comm


def create_pure_node_row(size, place_of_one=None):
    '''
    function to create a row with 'pure' nodes in Theta matrix
    size = Theta.shape[1] (Theta.shape[1] = number of communities)
    place_of_one = index of 1 in this row
    returns
    _______________________________________________
    nd.array with shape (size, )
    '''
    assert 0 <= place_of_one < size, "place_of_one >= size or < 0"
    return np.array([0] * place_of_one + [1] + [0]*(size - 1 - place_of_one))


def generate_theta(n_nodes, n_clusters, pure_nodes_number, alphas=None, seed=None):
    '''
    function to generate Theta matrix
    n_nodes = number of nodes
    n_clusters = number of communities
    pure_node_numbers = number of pure nodes in graph
    alphas = array in np.random.dirichlet
    returns
    _______________________________________________
    Theta: nd.array with shape (n_nodes, n_clusters)
    '''

    if seed is not None:
        np.random.seed(seed)

    assert n_nodes >= n_clusters > 0, "n_clusters > n_nodes"
    assert 0 <= pure_nodes_number <= n_nodes, "number of pure nodes is not in [0; n_nodes]"

    if alphas is None:
        alphas = [1. / n_clusters] * n_clusters  ## default value is alpha = [1/k,..,1/k], k=n_clusters
    else:
        assert len(alphas) == n_clusters, "len of alphas != n_clusters"

    ### we generate two matrix. The first one is the matrix with only pure_nodes
    ### the second matrix is from dirichlet distribution
    ### further we concat them along axis=0
    
    dirichlet_node_distribution = np.random.dirichlet(alphas, size=n_nodes - pure_nodes_number)
    pure_node_matrix = []
    
    for pure_node_idx in range(pure_nodes_number):
        pure_node_place = np.random.randint(low=0, high=n_clusters)
        pure_row = create_pure_node_row(n_clusters, pure_node_idx % n_clusters)
        pure_node_matrix.append(pure_row)

    pure_node_matrix = np.array(pure_node_matrix).reshape((pure_nodes_number, n_clusters))
    Theta = np.vstack([dirichlet_node_distribution, pure_node_matrix])
    Theta = np.random.permutation(Theta)
    return Theta

def generate_theta_binary(n_nodes):
    '''
    function to generate fixed binary matrix Theta (check SAAC with overlaps)
    '''
    block_size = n_nodes // 6
    Theta = [[1, 0, 0] for _ in range(block_size + (n_nodes - 6 * block_size))] + \
            [[0, 1, 0] for _ in range(block_size)] + \
            [[0, 0, 1] for _ in range(block_size)] + \
            [[1, 1, 0] for _ in range(block_size)] + \
            [[0, 1, 1] for _ in range(block_size)] + \
            [[1, 0, 1] for _ in range(block_size)]

    Theta2 = np.array(Theta)

    return Theta2 / np.sum(Theta2, axis=1, keepdims=True)


def generate_theta_bin_pure(n_nodes):
    '''
    function to generate fixed binary Theta matrix with pure nodes (check SAAC with overlaps)
    '''
    block_size = n_nodes // 3
    Theta = [[1, 0, 0] for _ in range(block_size + (n_nodes - 3 * block_size))] + \
            [[0, 1, 0] for _ in range(block_size)] + \
            [[0, 0, 1] for _ in range(block_size)]

    Theta2 = np.array(Theta)

    return Theta2 / np.sum(Theta2, axis=1, keepdims=True)


def generate_p(n_nodes=5000, n_clusters=3, pure_nodes_number=None, B=None, Theta=None, alphas=None, seed=None):
    '''
    function to generate P matrix from Theta, B matrices
    returns
    _______________________________________________
    P: np.array with shape (n_nodes, n_nodes)
    Theta: np.array with shape (n_nodes, n_clusters)
    B: np.array with shape (n_clusters, n_clusters)
    '''
    if seed is not None:
        np.random.seed(seed)

    if pure_nodes_number is None:
        pure_nodes_number = n_clusters
    else:
        assert 0 <= pure_nodes_number <= n_nodes, "number of pure nodes is not in (0; n_nodes)"
        
    if alphas is None:
        alphas = [1. / n_clusters] * n_clusters
    else:
        assert len(alphas) == n_clusters, "len of alphas != n_clusters"
        
    if Theta is None:
        Theta = generate_theta(n_nodes, n_clusters, pure_nodes_number, alphas, seed=seed)
    else:
        assert Theta.shape == (n_nodes, n_clusters), "Theta.shape != (n_nodes, n_clusters)"
        
    if B is None:
        B = np.diag(np.random.random(n_clusters))
    else:
        assert B.shape == (n_clusters, n_clusters), "B.shape != (n_clusters, n_clusters)"

    assert n_nodes >= n_clusters, "n_clusters > n_nodes"

    P = Theta.dot(B).dot(Theta.T)
    return P, Theta, B


def P_to_A(P, reflect = True, seed=None):
    '''
    function to generate A (adjacency matrix) from P (from bernoulli distribution)
    reflect parametrs is a flag to reflect elements in A symmetrically along diagonal,
    default value is True
    returns
    _______________________________________________
    A: np.array with shape (n_nodes, n_nodes)
    '''
    if seed is not None:
        sp.random.seed(seed)
    A = sp.stats.bernoulli.rvs(P, random_state=seed)

    ### we reflect elements in A symmetrically along diagonal
    if reflect == True:
        i_lower = np.tril_indices(P.shape[0], -1)
        A[i_lower] = A.T[i_lower]
        return 1.*A
    return 1. * A


def generate_a(n_nodes=5000, n_clusters=3, pure_nodes_number=None, B=None, Theta=None, reflect=True, alphas=None, seed=None):
    '''
    generate A matrix from params
    using P_to_A
    returns
    _______________________________________________
    A: np.array with shape (n_nodes, n_nodes)
    Theta: np.array with shape (n_nodes, n_clusters)
    B: np.array with shape (n_clusters, n_clusters)
    '''
    P, Theta, B = generate_p(n_nodes, n_clusters, pure_nodes_number, B, Theta, alphas, seed=seed)
    A = P_to_A(P, reflect=reflect)
    return A, Theta, B

def models_param():
    """
    Iterator for experiments on model data.
    :return:
    """
    np.random.seed(12312)
    n_nodes = 500
    n_clusters = 3
    pure_nodes_number = 3

    epss = np.arange(0.1, 0.4, 0.1)
    for eps in epss:
        print(eps)
        B = np.diag([0.5 - eps, 0.5, 0.5 + eps])
        Theta = generate_theta(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number)
        A, Theta, B = generate_a(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number, B=B,
                                 Theta=Theta)

        args = {
            'experiment name': 'Skewed B',
            'clusters': n_clusters,
            'nodes': n_nodes,
            'x': eps,
            'x name': 'B_eps',
            'alpha': 1 / n_clusters,
            'pure nodes number': pure_nodes_number,
        }
        yield A, Theta, B, args
    epss = [1e-3, 5e-3, 1e-2, 5e-2, 1e-1]

    for eps in epss:
        print(eps)
        B = eps * np.ones((n_clusters, n_clusters))
        np.fill_diagonal(B, 0.5)
        Theta = generate_theta(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number)
        A, Theta, B = generate_a(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number, B=B,
                                 Theta=Theta)

        args = {
            'experiment name': 'Noisy off-diag in B',
            'clusters': n_clusters,
            'nodes': n_nodes,
            'x': np.log10(eps),
            'x name': 'log10 eps',
            'alpha': 1 / n_clusters,
            'pure nodes number': pure_nodes_number,
        }
        yield A, Theta, B, args

    B = np.diag([0.3, 0.5, 0.7])
    alphas = np.arange(0.1, 0.7, 0.1)
    for alpha in alphas:
        print(eps)
        Theta = generate_theta(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number,
                               alphas=[alpha] * n_clusters)
        A, Theta, B = generate_a(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number, B=B,
                                 Theta=Theta, alphas=[alpha] * n_clusters)
        args = {
            'experiment name': 'Varying Dirichlet alpha',
            'clusters': n_clusters,
            'nodes': n_nodes,
            'x': alpha,
            'x name': 'alpha',
            'alpha': alpha,
            'pure nodes number': pure_nodes_number,
        }
        yield A, Theta, B, args

    B = np.diag([0.3, 0.5, 0.7])
    pnns = np.arange(3, min(1500, n_nodes), 100)
    for pnn in pnns:
        print(eps)
        Theta = generate_theta(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pnn, )
        A, Theta, B = generate_a(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pnn, B=B,
                                 Theta=Theta)
        args = {
            'experiment name': 'Varying pure nodes number',
            'clusters': n_clusters,
            'nodes': n_nodes,
            'x': pnn,
            'x name': 'pure nodes number',
            'alpha': 1 / n_clusters,
            'pure nodes number': pnn,
        }
        yield A, Theta, B, args
    ns = 500 + np.arange(500, 10000, 1000)
    ns[-1] += 500
    for n in ns:
        print(eps)
        B = np.diag([0.3, 0.5, 0.7])
        Theta = generate_theta(n_nodes=n, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number)
        A, Theta, B = generate_a(n_nodes=n, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number, B=B,
                                 Theta=Theta)

        args = {
            'experiment name': 'Varying nodes number',
            'clusters': n_clusters,
            'nodes': n,
            'x': n,
            'x name': 'nodes number',
            'alpha': 1 / n_clusters,
            'pure nodes number': pure_nodes_number,
        }
        yield A, Theta, B, args

    n_nodes = 500
    ns[-1] += 500
    pure_nodes_number = 3
    Rho = [1, 0.75, 0.5, 0.3, 0.2, 0.15, 0.1, 0.075, 0.05, 0.025, 0.01, 0.001]
    for rho in Rho:
        print(rho)
        B = rho * np.diag([0.3, 0.5, 0.7])
        Theta = generate_theta(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number)
        A, Theta, B = generate_a(n_nodes=n_nodes, n_clusters=n_clusters, pure_nodes_number=pure_nodes_number, B=B,
                                 Theta=Theta)

        args = {
            'experiment name': 'Varying B multiplier (rho)',
            'clusters': n_clusters,
            'nodes': n_nodes,
            'x': rho,
            'x name': 'rho',
            'alpha': 1 / n_clusters,
            'pure nodes number': pure_nodes_number,
        }
        yield A, Theta, B, args