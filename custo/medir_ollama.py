"""Mede uma inferência direto no Ollama (Etapa 6, TI Verde): tempo de carga, tokens e tempo total.

Uso: python custo/medir_ollama.py relatorios/r3-alta.txt
Rodar com o Ollama na CPU e depois na GPU (docker-compose.gpu.yml) para comparar.
"""
import json
import sys
import urllib.request

texto = open(sys.argv[1], encoding="utf-8").read().strip()
corpo = {
    "model": "llama3.2",
    "prompt": f"{texto}\nClassifique a urgência (baixa, media ou alta) e resuma em até 2 frases.",
    "stream": False,
    "options": {"temperature": 0, "num_predict": 80},
}
req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(corpo).encode(),
                             headers={"Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=600))
seg = lambda campo: r[campo] / 1e9  # o Ollama devolve as durações em nanossegundos
print(f"carga {seg('load_duration'):.1f} s | entrada {r['prompt_eval_count']} tokens | "
      f"saída {r['eval_count']} tokens | geração {seg('eval_duration'):.1f} s | total {seg('total_duration'):.1f} s")
