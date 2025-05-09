import numpy as np

from tensortree import util


def jukes_cantor(mue=4./3, d=4, dtype=util.default_dtype):
    """ Returns the exchangeabilities and equilibrium frequencies for the 
    Jukes-Cantor model.

    Args:
        mue: Scalar, list or 1D array.

    Returns:
        symmetric k x d x d  tensor of exchangeabilities and k x d matrix of 
            equilibrium frequencies.
        k is the length of mue or 1 if mue is a scalar.
    """
    if isinstance(mue, list):
        mue = np.array(mue, dtype=dtype)
    if np.isscalar(mue):
        mue = np.array([mue], dtype=dtype)
    assert(mue.ndim == 1)
    I = (1-np.eye(d, dtype=dtype))
    I = np.stack([I]*mue.size)
    exchangeabilities = I * mue[:, np.newaxis, np.newaxis]
    equilibrium = np.ones((mue.size, d), dtype=dtype) / d
    return exchangeabilities, equilibrium




def LG(alphabet="ARNDCQEGHILKMFPSTWYV", dtype=util.default_dtype):
    """ Returns the exchangeabilities and equilibrium frequencies for the LG 
        model.
        Use for amino acids.

    Args:
        alphabet: A string with the amino acids in the desired order.   
        
    Returns:
        symmetric d x d  tensor of exchangeabilities and d matrix of 
        equilibrium frequencies.
    """
    return parse_paml(LG_paml, alphabet)


def parse_paml(lines, desired_alphabet):
    """Parses the content of a paml file.

    Returns:
        A symmetric exchangeability matrix with zero diagonal and a frequency 
        vector.
    """
    paml_alphabet = "A R N D C Q E G H I L K M F P S T W Y V".split(" ")
    s = len(paml_alphabet)
    R = np.zeros((s, s), dtype=np.float32)
    for i in range(1,s):
        R[i,:i] = R[:i,i] = np.fromstring(lines[i-1], sep=" ") 
    p = np.fromstring(lines[s-1], sep=" ", dtype=np.float32)
    #reorganize to match the amino acid order in desired_alphabet
    perm = [
        paml_alphabet.index(aa) 
        for aa in desired_alphabet if aa in paml_alphabet
    ]
    p = p[perm]
    R = R[perm, :]
    R = R[:, perm]
    return R, p


# the default rate matrix ("LG")
LG_paml = ['0.425093 \n', 
           '0.276818 0.751878 \n', 
           '0.395144 0.123954 5.076149 \n', 
           '2.489084 0.534551 0.528768 0.062556 \n', 
           '0.969894 2.807908 1.695752 0.523386 0.084808 \n', 
           '1.038545 0.363970 0.541712 5.243870 0.003499 4.128591 \n', 
           '2.066040 0.390192 1.437645 0.844926 0.569265 0.267959 0.348847 \n', 
           '0.358858 2.426601 4.509238 0.927114 0.640543 4.813505 0.423881 0.311484 \n', 
           '0.149830 0.126991 0.191503 0.010690 0.320627 0.072854 0.044265 0.008705 0.108882 \n', 
           '0.395337 0.301848 0.068427 0.015076 0.594007 0.582457 0.069673 0.044261 0.366317 4.145067 \n', 
           '0.536518 6.326067 2.145078 0.282959 0.013266 3.234294 1.807177 0.296636 0.697264 0.159069 0.137500 \n',
           '1.124035 0.484133 0.371004 0.025548 0.893680 1.672569 0.173735 0.139538 0.442472 4.273607 6.312358 0.656604 \n', 
           '0.253701 0.052722 0.089525 0.017416 1.105251 0.035855 0.018811 0.089586 0.682139 1.112727 2.592692 0.023918 1.798853 \n', 
           '1.177651 0.332533 0.161787 0.394456 0.075382 0.624294 0.419409 0.196961 0.508851 0.078281 0.249060 0.390322 0.099849 0.094464 \n', 
           '4.727182 0.858151 4.008358 1.240275 2.784478 1.223828 0.611973 1.739990 0.990012 0.064105 0.182287 0.748683 0.346960 0.361819 1.338132 \n', 
           '2.139501 0.578987 2.000679 0.425860 1.143480 1.080136 0.604545 0.129836 0.584262 1.033739 0.302936 1.136863 2.020366 0.165001 0.571468 6.472279 \n', 
           '0.180717 0.593607 0.045376 0.029890 0.670128 0.236199 0.077852 0.268491 0.597054 0.111660 0.619632 0.049906 0.696175 2.457121 0.095131 0.248862 0.140825 \n', 
           '0.218959 0.314440 0.612025 0.135107 1.165532 0.257336 0.120037 0.054679 5.306834 0.232523 0.299648 0.131932 0.481306 7.803902 0.089613 0.400547 0.245841 3.151815 \n', 
           '2.547870 0.170887 0.083688 0.037967 1.959291 0.210332 0.245034 0.076701 0.119013 10.649107 1.702745 0.185202 1.898718 0.654683 0.296501 0.098369 2.188158 0.189510 0.249313 \n', 
           '0.079066 0.055941 0.041977 0.053052 0.012937 0.040767 0.071586 0.057337 0.022355 0.062157 0.099081 0.064600 0.022951 0.042302 0.044040 0.061197 0.053287 0.012066 0.034155 0.069147 \n']
