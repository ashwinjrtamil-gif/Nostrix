import torch
from torch import nn
import torch.nn.functional as F

# -------------------- CUSTOM LANGUAGE MODEL --------------------
class NostrixM1LM(nn.Module):
    def __init__(self, vocab_size=5000, d_model=256, nhead=4, num_layers=2, dim_feedforward=512, max_len=512):
        super().__init__()
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.max_len = max_len
        
        # Token embedding + positional embedding
        self.token_embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_len, d_model)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=dim_feedforward)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Output projection
        self.fc_out = nn.Linear(d_model, vocab_size)
    
    def forward(self, x):
        # x: (batch, seq_len)
        seq_len = x.size(1)
        positions = torch.arange(0, seq_len, device=x.device).unsqueeze(0)
        x = self.token_embed(x) + self.pos_embed(positions)
        x = self.transformer(x.transpose(0,1)).transpose(0,1)  # (batch, seq_len, d_model)
        logits = self.fc_out(x)
        return logits  # (batch, seq_len, vocab_size)
    
    def generate(self, input_tokens, max_new_tokens=50, temperature=0.8, top_k=50):
        self.eval()
        generated = input_tokens.clone()
        for _ in range(max_new_tokens):
            logits = self.forward(generated)
            next_token_logits = logits[:, -1, :] / temperature
            # Top-k sampling
            topk_vals, topk_idx = torch.topk(next_token_logits, top_k)
            probs = F.softmax(topk_vals, dim=-1)
            next_token = topk_idx[torch.multinomial(probs, num_samples=1)]
            generated = torch.cat([generated, next_token.unsqueeze(0)], dim=1)
        return generated
