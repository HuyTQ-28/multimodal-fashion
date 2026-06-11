import numpy as np

# Load the .npy file
data = np.load('D:/recsys/multimodal-fashion/dataset/saved/teacher_item_128.npy')

# Inspect the content and structural attributes
print("Array Data:\n", data)
print("Shape:", data.shape)
print("Data Type:", data.dtype)