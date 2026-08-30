"""
GlucoShield GPU Smoke Test
Creates CUDA tensors, GRU model, runs forward/backward/optimizer step on GPU.
Holds GPU memory for nvidia-smi verification.
"""
import torch
import torch.nn as nn
import time

print("=" * 60)
print("GPU SMOKE TEST")
print("=" * 60)

# 1. Basic CUDA verification
print(f"\nPYTORCH VERSION:      {torch.__version__}")
print(f"CUDA AVAILABLE:       {torch.cuda.is_available()}")
print(f"PYTORCH CUDA VERSION: {torch.version.cuda}")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"SELECTED DEVICE:      {device}")

if not torch.cuda.is_available():
    print("\nFAIL: CUDA not available. Aborting smoke test.")
    exit(1)

print(f"GPU NAME:             {torch.cuda.get_device_name(0)}")
print(f"GPU MEMORY TOTAL:     {torch.cuda.get_device_properties(0).total_memory / 1024**2:.0f} MiB")

# 2. Create CUDA tensor
print("\n--- Creating CUDA tensors ---")
x = torch.randn(256, 96, 22, device=device)  # batch, seq_len, features
static = torch.randn(256, 9, device=device)
target_traj = torch.randn(256, 20, device=device)
target_risk = torch.randint(0, 2, (256, 5), device=device).float()
print(f"  Input tensor:  {x.shape} on {x.device}")
print(f"  Static tensor: {static.shape} on {static.device}")

# 3. Create GRU model and move to CUDA
print("\n--- Creating GRU model on CUDA ---")
class SmokeGRU(nn.Module):
    def __init__(self):
        super().__init__()
        self.gru = nn.GRU(22, 128, num_layers=1, batch_first=True, dropout=0.0)
        self.static_mlp = nn.Sequential(nn.Linear(9, 32), nn.ReLU(), nn.Linear(32, 32))
        self.traj_head = nn.Linear(128 + 32, 20)
        self.risk_head = nn.Linear(128 + 32, 5)

    def forward(self, x, s):
        out, _ = self.gru(x)
        h = out[:, -1, :]
        s_enc = self.static_mlp(s)
        fused = torch.cat([h, s_enc], dim=-1)
        return self.traj_head(fused), torch.sigmoid(self.risk_head(fused))

model = SmokeGRU().to(device)
print(f"  Model on device: {next(model.parameters()).device}")
total_params = sum(p.numel() for p in model.parameters())
print(f"  Total parameters: {total_params:,}")

# 4. Forward pass
print("\n--- Forward pass ---")
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
pred_traj, pred_risk = model(x, static)
print(f"  Trajectory pred shape: {pred_traj.shape} on {pred_traj.device}")
print(f"  Risk pred shape:       {pred_risk.shape} on {pred_risk.device}")

# 5. Backward pass
print("\n--- Backward pass ---")
loss_traj = nn.HuberLoss()(pred_traj, target_traj)
loss_risk = nn.BCELoss()(pred_risk, target_risk)
loss = loss_traj + loss_risk
loss.backward()
print(f"  Loss: {loss.item():.4f}")
print(f"  Grad norm (GRU weight): {model.gru.weight_ih_l0.grad.norm().item():.6f}")

# 6. Optimizer step
print("\n--- Optimizer step ---")
optimizer.step()
optimizer.zero_grad()
print("  Optimizer step completed successfully.")

# 7. Check GPU memory usage
allocated = torch.cuda.memory_allocated(0) / 1024**2
reserved = torch.cuda.memory_reserved(0) / 1024**2
print(f"\n  GPU Memory Allocated: {allocated:.1f} MiB")
print(f"  GPU Memory Reserved:  {reserved:.1f} MiB")

# 8. Hold GPU memory for nvidia-smi verification
print("\n--- Holding GPU memory for 15 seconds for nvidia-smi verification ---")
print("  Run 'nvidia-smi' in another terminal NOW to verify GPU process.")
# Allocate extra memory to make it clearly visible
big_tensor = torch.randn(2048, 2048, device=device)
allocated2 = torch.cuda.memory_allocated(0) / 1024**2
print(f"  GPU Memory Allocated (with extra tensor): {allocated2:.1f} MiB")
time.sleep(15)

print("\n" + "=" * 60)
print("GPU SMOKE TEST: ALL PASSED")
print("=" * 60)
