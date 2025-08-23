import torch
import numpy as np


class ModelService:
    def __init__(
        self,
        model ,
        preprocess ,
        tokenizer ,
        device: str='cuda'
        ):
        self.model = model
        self.device = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = model.to(self.device)
        self.preprocess = preprocess
        self.tokenizer = tokenizer
        self.model.eval()
    
    def embedding(self, query_text: str) -> np.ndarray:
        """
        Return (1, ndim 1024) torch.Tensor
        """
        with torch.no_grad():
            text_tokens = self.tokenizer([query_text]).to(self.device)
            query_embedding = self.model.encode_text(text_tokens).cpu().detach().numpy().astype(np.float32) # (1, 1024)
        return query_embedding

            