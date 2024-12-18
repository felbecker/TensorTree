from tensortree.tree_handler import TreeHandler
from tensortree.util import backend
import numpy as np




"""
Traverse n independent branches {u, parent(u)} in parallel, i.e. compute the log-likelihoods 
of all symbols at parent(u) given the log-likelihoods at u.
Does not aggregate.
Args:
    X: Log-likelihoods of shape (n, models, L, d)
    branch_lengths: Branch lengths of shape (n, models)
    rate_matrix: Rate matrix of shape (models, d, d)
    transposed: If True, a transposed transition matrix (X is past, T is present) will be used. 
                Per default, the transition matrix is not transposed, i.e. X is present and T is past.
                When transposed=True, T will be (log-)probabilities, given X are also (log-)probabilities.
"""
def traverse_branches(X, rate_matrix, branch_lengths, transposed=False, logarithmic=True):
    P = backend.make_transition_probs(rate_matrix, branch_lengths)
    T = backend.traverse_branch(X, P, transposed, logarithmic=logarithmic)
    return T


"""
Computes the partial log-likelihoods at all internal (ancestral) nodes in the tree 
given logits at the leaves and a tree topology.
Supports multiple models with broadcasting for rates and leaves in the model dimension.
Uses a vectorized implementation of Felsenstein's pruning algorithm
that treats models, sequence positions and all nodes within a tree layer in parallel.
Args:
    leaves: Logits of all symbols at all leaves of shape (num_leaves, models, L, d). 
    leaf_names: Names of the leaves (list-like of length num_leaves). Used to reorder correctly.
    tree_handler: TreeHandler object
    rate_matrix: Rate matrix of shape (models, d, d)
    branch_lengths: Branch lengths of shape (num_nodes-1, models)
    return_only_root: If True, only the root node logits are returned.
    leaves_are_probabilities: If True, leaves are assumed to be probabilities or one-hot encoded.
    return_probabilities: If True, return probabilities instead of logits.
Returns:
    Ancestral logits of shape (models, L, d) if return_only_root 
    else shape (num_ancestral_nodes, models, L, d)
"""
def compute_ancestral_probabilities(leaves, leaf_names,
                                    tree_handler : TreeHandler, rate_matrix, branch_lengths, 
                                    return_only_root = False, leaves_are_probabilities = False,
                                    return_probabilities = False):
    
    if leaves_are_probabilities:
        leaves = backend.logits_from_probs(leaves)

    # allocate a single chunk of memory for all internal nodes (no concat or masking required)
    # add results as layers are processed
    anc_logliks = backend.get_ancestral_logits_init_tensor(leaves, tree_handler.num_models, tree_handler.num_anc)

    # reorder the leaves to match the tree handler's internal order
    X = tree_handler.reorder(leaves, leaf_names)
    
    for height in range(tree_handler.height):
        
        # traverse all edges {u, parent(u)} for all u of same height in parallel
        B = tree_handler.get_values_by_height(branch_lengths, height)
        T = traverse_branches(X, rate_matrix, B)

        # aggregate over child nodes with the same parent and add to anc_logliks
        parent_indices = tree_handler.get_parent_indices_by_height(height)
        Z = backend.aggregate_children_log_probs(T, parent_indices-tree_handler.num_leaves, tree_handler.num_anc)
        anc_logliks += Z

        X = tree_handler.get_values_by_height(anc_logliks, height+1, leaves_included=False)

    if return_only_root:
        anc_logliks = anc_logliks[-1]

    return backend.probs_from_logits(anc_logliks) if return_probabilities else anc_logliks


"""
Computes log P(leaves | tree, rate_matrix).
Args:
    leaves: Logits of all symbols at all leaves of shape (num_leaves, models, L, d).
    tree_handler: TreeHandler object
    rate_matrix: Rate matrix of shape (models, d, d)
    branch_lengths: Branch lengths of shape (num_nodes-1, models)
    equilibrium_logits: Equilibrium distribution logits of shape (models, d).
    leaves_are_probabilities: If True, leaves are assumed to be probabilities or one-hot encoded.
Returns:
    Log-likelihoods of shape (models, L).
"""
def loglik(leaves, leaf_names, tree_handler : TreeHandler, rate_matrix, branch_lengths, equilibrium_logits, 
           leaves_are_probabilities=False):
    root_logits = compute_ancestral_probabilities(leaves, leaf_names, tree_handler, rate_matrix, branch_lengths,
                                                  return_only_root = True, leaves_are_probabilities=leaves_are_probabilities, 
                                                  return_probabilities=False)
    return backend.loglik_from_root_logits(root_logits, equilibrium_logits)