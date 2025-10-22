GPU Not Being Used
==================

- If your GPU is not being utilized as expected, ensure that the variable `limit_gpu` in **KaapanaBaseOperator** is not set to `None`.

- The operator should request GPU memory via `gpuMem`, and the request must be compatible with the available GPU's capabilities.

Additionally, ensure that the versions of **CUDA** and the **GPU drivers** are properly matched:

- Run `nvidia-smi` to check the installed NVIDIA driver version.
- Run `nvcc --version` to verify the CUDA compiler version.

For optimal compatibility:

- The version reported by `nvidia-smi` (NVIDIA driver version) should be **greater than or equal to** the version reported by `nvcc` (CUDA version).

For more details on version mismatches, refer to `StackOverflow - Different CUDA versions shown by nvcc and nvidia-smi <https://stackoverflow.com/questions/53422407/different-cuda-versions-shown-by-nvcc-and-nvidia-smi>`_.