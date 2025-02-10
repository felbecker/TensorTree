import torch
import numpy as np
from Bio.Phylo import BaseTree
from functools import partial
from tensortree import util



def _ensure_tensor(x):
    if isinstance(x, np.ndarray):
        return torch.from_numpy(x)
    if isinstance(x, list):
        return torch.tensor(x)
    return x


# Documentation in the base class. Hover over the method name to see the docstring.
class BackendTorch(util.Backend):

    def make_rate_matrix(self, exchangeabilities, equilibrium, epsilon=1e-16, normalized=True):
        exchangeabilities = _ensure_tensor(exchangeabilities)
        equilibrium = _ensure_tensor(equilibrium)
        Q = torch.mul(exchangeabilities, equilibrium[:,None])
        diag = torch.sum(Q, -1, True)
        eye = torch.eye(diag.shape[1], dtype=diag.dtype, device=diag.device)
        eye = eye[None]
        eye = eye.repeat(diag.shape[0], 1, 1)
        Q -= diag * eye
        # normalize
        if normalized:
            mue = equilibrium[..., None] * diag
            mue = torch.sum(mue, dim=-2, keepdim=True)
            Q /= torch.maximum(mue, torch.tensor(epsilon))
        return Q


    def make_transition_probs(self, rate_matrix, distances):
        rate_matrix = _ensure_tensor(rate_matrix)
        distances = _ensure_tensor(distances)
        rate_matrix = rate_matrix[None]
        distances = distances[..., None, None]
        P = torch.linalg.matrix_exp(rate_matrix * distances) # P[b,m,i,j] = P(X(tau_b) = j | X(0) = i; model m))
        return P


    def make_branch_lengths(self, kernel):
        kernel = _ensure_tensor(kernel)
        return torch.nn.functional.softplus(kernel)


    def make_symmetric_pos_semidefinite(self, kernel):
        R = 0.5 * (kernel + kernel.permute((0,2,1))) #make symmetric
        R = torch.nn.functional.softplus(R)
        R -= torch.diag(torch.diagonal(R)) #zero diagonal
        return R


    def make_equilibrium(self, kernel):
        return torch.nn.functional.softmax(kernel, dim=-1)


    def traverse_branch(self, X, branch_probabilities, transposed=False, logarithmic=True):
        if logarithmic:
            X = self.probs_from_logits(X)
        if transposed:
            X = torch.einsum("nkLd,nkdz->nkLz", X, branch_probabilities)
        else:
            X = torch.einsum("nkLd,nkzd->nkLz", X, branch_probabilities)
        if logarithmic:
            X = self.logits_from_probs(X)
        return X


    def aggregate_children_log_probs(self, X, parent_map, num_ancestral):
        parent_map = _ensure_tensor(parent_map).to(X.device)
        #return tf.math.unsorted_segment_sum(X, parent_map, num_ancestral)
        Y = torch.zeros(num_ancestral, *X.shape[1:], dtype=X.dtype, device=X.device)
        I = parent_map[:,None,None,None].expand(X.shape)
        Y = Y.scatter_add(0, I, X)
        return Y


    def loglik_from_root_logits(self, root_logits, equilibrium_logits):
        return torch.logsumexp(root_logits + equilibrium_logits[:,None], dim=-1)
    

    def marginals_from_beliefs(self, beliefs):
        loglik = torch.logsumexp(beliefs[-1:], dim=-1, keepdim=True)
        return beliefs - loglik


    def logits_from_probs(self, probs, log_zero_val=-1e3):
        probs = _ensure_tensor(probs)
        epsilon = torch.tensor(np.finfo(util.default_dtype).tiny)
        logits = torch.log(torch.maximum(probs, epsilon))
        zero_mask = (probs == 0).to(logits.dtype)
        logits = (1-zero_mask) * logits + zero_mask * log_zero_val
        return logits


    def probs_from_logits(self, logits):
        return torch.exp(logits)


    def gather(self, tensor, indices, axis=0):
        tensor = _ensure_tensor(tensor)
        indices = _ensure_tensor(indices)
        return tensor[indices]


    def concat(self, tensors, axis=0):
        return torch.cat(tensors, axis=axis)


    def make_zeros(self, leaves, models, num_nodes):
        return torch.zeros((num_nodes, models, leaves.shape[-2], leaves.shape[-1]), 
                        dtype=leaves.dtype, device=leaves.device)