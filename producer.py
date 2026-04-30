import os
import time
from datetime import datetime
from tasks import execute_resize_batch, BATCH_ORDER_FILE, ITEM_ORDER_FILE


def log(message: str):
    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{now}] [PRODUCER] {message}", flush=True)


def reset_files():
    for path in (BATCH_ORDER_FILE, ITEM_ORDER_FILE):
        if os.path.exists(path):
            os.remove(path)


def read_lines(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip()]


batches = {
    "AAA": [f"A{i}" for i in range(1, 6)],
    "BBB": [f"B{i}" for i in range(1, 6)],
    "CCC": [f"C{i}" for i in range(1, 6)],
}

total_items = sum(len(v) for v in batches.values())

reset_files()
log("Arquivos de ordem zerados (/tmp/celery_test_*.log)")
log("Iniciando envio dos lotes para a fila batch_queue")

for batch_id, items in batches.items():
    log(f"Enfileirando lote {batch_id} com {len(items)} itens")
    execute_resize_batch.delay(batch_id, items)

log("Todos os lotes foram enfileirados. Aguardando processamento...")

deadline = time.time() + 60
while time.time() < deadline:
    batch_done = len(read_lines(BATCH_ORDER_FILE)) >= len(batches)
    items_done = len(read_lines(ITEM_ORDER_FILE)) >= total_items
    if batch_done and items_done:
        break
    time.sleep(0.5)

print()
print("=" * 70)
print("RESUMO VISUAL DO TESTE")
print("=" * 70)

batch_order = read_lines(BATCH_ORDER_FILE)
print()
print("[FILA DE ORQUESTRACAO] Ordem em que os lotes foram processados:")
print(f"   {batch_order}")
print()

item_lines = read_lines(ITEM_ORDER_FILE)
print("[FILA DE EXECUCAO] Ordem de conclusao dos itens:")
print(f"{'#':>3}  {'LOTE':<6} {'ITEM':<6} WORKER")
print("-" * 70)
for idx, line in enumerate(item_lines, start=1):
    parts = line.split("\t")
    if len(parts) == 3:
        b, i, w = parts
        print(f"{idx:>3}  {b:<6} {i:<6} {w}")

print()
print("[DISTRIBUICAO POR WORKER]")
counter: dict[str, int] = {}
for line in item_lines:
    parts = line.split("\t")
    if len(parts) == 3:
        counter[parts[2]] = counter.get(parts[2], 0) + 1
for w, n in sorted(counter.items()):
    print(f"   {w}: {n} item(ns)")
print("=" * 70)
